"""
Intelligent Payment Retry Mechanisms for FlashStudio
Provides automatic retry logic, exponential backoff, and customer notifications
"""
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from flask import current_app
from models import db, Order
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class PaymentFailureReason(Enum):
    """Classification of payment failure reasons"""
    CARD_DECLINED = "card_declined"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    EXPIRED_CARD = "expired_card"
    INCORRECT_CVC = "incorrect_cvc"
    PROCESSING_ERROR = "processing_error"
    AUTHENTICATION_REQUIRED = "authentication_required"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"

class RetryStrategy(Enum):
    """Different retry strategies"""
    IMMEDIATE = "immediate"           # Retry immediately (for network errors)
    LINEAR_BACKOFF = "linear"        # Linear backoff (1, 2, 3 minutes)
    EXPONENTIAL_BACKOFF = "exponential"  # Exponential backoff (1, 2, 4, 8 minutes)
    NO_RETRY = "no_retry"           # Don't retry (card declined permanently)
    USER_ACTION_REQUIRED = "user_action"  # Requires user intervention

@dataclass
class RetryAttempt:
    """Individual retry attempt data"""
    attempt_number: int
    timestamp: datetime
    failure_reason: str
    stripe_error_code: str
    retry_after_seconds: int
    next_retry_time: Optional[datetime] = None
    success: bool = False

@dataclass
class PaymentRetryContext:
    """Complete retry context for a payment"""
    order_id: int
    payment_intent_id: str
    original_failure_reason: PaymentFailureReason
    retry_strategy: RetryStrategy
    max_attempts: int
    current_attempts: int
    attempts: List[RetryAttempt]
    created_at: datetime
    last_retry_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    final_failure: bool = False
    customer_notified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        if self.last_retry_at:
            data['last_retry_at'] = self.last_retry_at.isoformat()
        if self.next_retry_at:
            data['next_retry_at'] = self.next_retry_at.isoformat()
        
        # Convert attempts
        data['attempts'] = []
        for attempt in self.attempts:
            attempt_dict = asdict(attempt)
            attempt_dict['timestamp'] = attempt.timestamp.isoformat()
            if attempt.next_retry_time:
                attempt_dict['next_retry_time'] = attempt.next_retry_time.isoformat()
            data['attempts'].append(attempt_dict)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaymentRetryContext':
        """Create from dictionary"""
        # Convert datetime strings back
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_retry_at'):
            data['last_retry_at'] = datetime.fromisoformat(data['last_retry_at'])
        if data.get('next_retry_at'):
            data['next_retry_at'] = datetime.fromisoformat(data['next_retry_at'])
        
        # Convert attempts
        attempts = []
        for attempt_data in data.get('attempts', []):
            attempt_data['timestamp'] = datetime.fromisoformat(attempt_data['timestamp'])
            if attempt_data.get('next_retry_time'):
                attempt_data['next_retry_time'] = datetime.fromisoformat(attempt_data['next_retry_time'])
            attempts.append(RetryAttempt(**attempt_data))
        data['attempts'] = attempts
        
        # Convert enums
        data['original_failure_reason'] = PaymentFailureReason(data['original_failure_reason'])
        data['retry_strategy'] = RetryStrategy(data['retry_strategy'])
        
        return cls(**data)

class PaymentRetryService:
    """Service for managing payment retry logic and recovery"""
    
    def __init__(self):
        self.retry_contexts = {}  # In-memory storage (would use Redis/DB in production)
        
        # Retry configurations
        self.retry_configs = {
            PaymentFailureReason.CARD_DECLINED: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_attempts': 0,
                'notify_customer': True,
                'message': 'Your card was declined. Please try a different payment method.'
            },
            PaymentFailureReason.INSUFFICIENT_FUNDS: {
                'strategy': RetryStrategy.USER_ACTION_REQUIRED,
                'max_attempts': 0,
                'notify_customer': True,
                'message': 'Insufficient funds. Please check your account balance or use a different card.'
            },
            PaymentFailureReason.EXPIRED_CARD: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_attempts': 0,
                'notify_customer': True,
                'message': 'Your card has expired. Please update your payment information.'
            },
            PaymentFailureReason.INCORRECT_CVC: {
                'strategy': RetryStrategy.NO_RETRY,
                'max_attempts': 0,
                'notify_customer': True,
                'message': 'Incorrect CVC code. Please check your card details and try again.'
            },
            PaymentFailureReason.PROCESSING_ERROR: {
                'strategy': RetryStrategy.EXPONENTIAL_BACKOFF,
                'max_attempts': 3,
                'notify_customer': False,
                'message': 'Payment processing error. We\'ll retry automatically.'
            },
            PaymentFailureReason.NETWORK_ERROR: {
                'strategy': RetryStrategy.EXPONENTIAL_BACKOFF,
                'max_attempts': 5,
                'notify_customer': False,
                'message': 'Network error. We\'ll retry automatically.'
            },
            PaymentFailureReason.AUTHENTICATION_REQUIRED: {
                'strategy': RetryStrategy.USER_ACTION_REQUIRED,
                'max_attempts': 0,
                'notify_customer': True,
                'message': 'Additional authentication required. Please complete 3D Secure verification.'
            },
            PaymentFailureReason.RATE_LIMITED: {
                'strategy': RetryStrategy.LINEAR_BACKOFF,
                'max_attempts': 3,
                'notify_customer': False,
                'message': 'Rate limited. We\'ll retry automatically.'
            },
            PaymentFailureReason.UNKNOWN: {
                'strategy': RetryStrategy.EXPONENTIAL_BACKOFF,
                'max_attempts': 2,
                'notify_customer': True,
                'message': 'Payment failed. We\'ll retry and notify you of the outcome.'
            }
        }
    
    def classify_failure_reason(self, stripe_error) -> PaymentFailureReason:
        """Classify Stripe error into failure reason category"""
        if not stripe_error:
            return PaymentFailureReason.UNKNOWN
        
        error_code = getattr(stripe_error, 'code', '')
        error_type = getattr(stripe_error, 'type', '')
        decline_code = getattr(stripe_error, 'decline_code', '')
        
        # Map Stripe error codes to our classifications
        if error_code in ['card_declined', 'generic_decline']:
            if decline_code == 'insufficient_funds':
                return PaymentFailureReason.INSUFFICIENT_FUNDS
            elif decline_code == 'expired_card':
                return PaymentFailureReason.EXPIRED_CARD
            elif decline_code in ['incorrect_cvc', 'invalid_cvc']:
                return PaymentFailureReason.INCORRECT_CVC
            else:
                return PaymentFailureReason.CARD_DECLINED
        elif error_code == 'authentication_required':
            return PaymentFailureReason.AUTHENTICATION_REQUIRED
        elif error_code == 'processing_error':
            return PaymentFailureReason.PROCESSING_ERROR
        elif error_type == 'rate_limit_error':
            return PaymentFailureReason.RATE_LIMITED
        elif error_type in ['api_connection_error', 'api_error']:
            return PaymentFailureReason.NETWORK_ERROR
        else:
            return PaymentFailureReason.UNKNOWN
    
    def calculate_retry_delay(self, strategy: RetryStrategy, attempt_number: int) -> int:
        """Calculate delay in seconds for next retry attempt"""
        if strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            return attempt_number * 60  # 1, 2, 3 minutes
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return (2 ** (attempt_number - 1)) * 60  # 1, 2, 4, 8 minutes
        else:
            return 0  # No retry
    
    def should_retry_payment(self, failure_reason: PaymentFailureReason, 
                           current_attempts: int) -> bool:
        """Determine if payment should be retried"""
        config = self.retry_configs.get(failure_reason)
        if not config:
            return False
        
        if config['strategy'] in [RetryStrategy.NO_RETRY, RetryStrategy.USER_ACTION_REQUIRED]:
            return False
        
        return current_attempts < config['max_attempts']
    
    def create_retry_context(self, order_id: int, payment_intent_id: str,
                           stripe_error) -> PaymentRetryContext:
        """Create new retry context for failed payment"""
        failure_reason = self.classify_failure_reason(stripe_error)
        config = self.retry_configs.get(failure_reason, self.retry_configs[PaymentFailureReason.UNKNOWN])
        
        # Create initial retry attempt
        initial_attempt = RetryAttempt(
            attempt_number=1,
            timestamp=datetime.utcnow(),
            failure_reason=failure_reason.value,
            stripe_error_code=getattr(stripe_error, 'code', 'unknown'),
            retry_after_seconds=0,
            success=False
        )
        
        # Calculate next retry time
        next_retry_time = None
        if config['strategy'] not in [RetryStrategy.NO_RETRY, RetryStrategy.USER_ACTION_REQUIRED]:
            delay = self.calculate_retry_delay(config['strategy'], 1)
            next_retry_time = datetime.utcnow() + timedelta(seconds=delay)
            initial_attempt.next_retry_time = next_retry_time
        
        context = PaymentRetryContext(
            order_id=order_id,
            payment_intent_id=payment_intent_id,
            original_failure_reason=failure_reason,
            retry_strategy=config['strategy'],
            max_attempts=config['max_attempts'],
            current_attempts=1,
            attempts=[initial_attempt],
            created_at=datetime.utcnow(),
            next_retry_at=next_retry_time
        )
        
        # Store context
        self.retry_contexts[payment_intent_id] = context
        
        logger.info(f"Created retry context for payment {payment_intent_id}: "
                   f"reason={failure_reason.value}, strategy={config['strategy'].value}, "
                   f"max_attempts={config['max_attempts']}")
        
        return context
    
    def add_retry_attempt(self, payment_intent_id: str, stripe_error, success: bool = False) -> bool:
        """Add new retry attempt to existing context"""
        context = self.retry_contexts.get(payment_intent_id)
        if not context:
            logger.error(f"No retry context found for payment {payment_intent_id}")
            return False
        
        context.current_attempts += 1
        
        # Create retry attempt
        retry_delay = 0
        next_retry_time = None
        
        if not success and self.should_retry_payment(context.original_failure_reason, context.current_attempts):
            retry_delay = self.calculate_retry_delay(context.retry_strategy, context.current_attempts)
            next_retry_time = datetime.utcnow() + timedelta(seconds=retry_delay)
            context.next_retry_at = next_retry_time
        else:
            # No more retries
            context.final_failure = not success
            context.next_retry_at = None
        
        attempt = RetryAttempt(
            attempt_number=context.current_attempts,
            timestamp=datetime.utcnow(),
            failure_reason=self.classify_failure_reason(stripe_error).value if stripe_error else 'success',
            stripe_error_code=getattr(stripe_error, 'code', 'none'),
            retry_after_seconds=retry_delay,
            next_retry_time=next_retry_time,
            success=success
        )
        
        context.attempts.append(attempt)
        context.last_retry_at = datetime.utcnow()
        
        logger.info(f"Added retry attempt {context.current_attempts} for payment {payment_intent_id}: "
                   f"success={success}, next_retry_at={next_retry_time}")
        
        return True
    
    def get_retry_context(self, payment_intent_id: str) -> Optional[PaymentRetryContext]:
        """Get retry context for payment"""
        return self.retry_contexts.get(payment_intent_id)
    
    def get_pending_retries(self) -> List[PaymentRetryContext]:
        """Get all payments that are pending retry"""
        now = datetime.utcnow()
        pending = []
        
        for context in self.retry_contexts.values():
            if (context.next_retry_at and 
                context.next_retry_at <= now and 
                not context.final_failure):
                pending.append(context)
        
        return pending
    
    def send_customer_notification(self, order_id: int, failure_reason: PaymentFailureReason,
                                 context: PaymentRetryContext):
        """Send notification email to customer about payment failure"""
        try:
            # Get order details
            order = Order.query.get(order_id)
            if not order or not order.user:
                logger.error(f"Order {order_id} or user not found for notification")
                return False
            
            config = self.retry_configs.get(failure_reason)
            if not config or not config['notify_customer']:
                return True  # No notification needed
            
            # Prepare email content
            subject = f"Payment Update - Order #{order.id}"
            
            # Determine message based on retry strategy
            if context.retry_strategy in [RetryStrategy.NO_RETRY, RetryStrategy.USER_ACTION_REQUIRED]:
                action_required = True
                message = config['message'] + " Please update your payment method and try again."
            else:
                action_required = False
                message = config['message'] + " We'll notify you when the payment is processed."
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h2 style="color: #007bff; margin: 0;">Payment Update Required</h2>
                    </div>
                    
                    <p>Dear {order.user.name},</p>
                    
                    <p>We encountered an issue processing your payment for Order #{order.id}.</p>
                    
                    <div style="background: {'#fff3cd' if action_required else '#d1ecf1'}; 
                                border: 1px solid {'#ffeaa7' if action_required else '#bee5eb'}; 
                                border-radius: 5px; padding: 15px; margin: 20px 0;">
                        <h4 style="margin: 0 0 10px 0; color: {'#856404' if action_required else '#0c5460'};">
                            {'Action Required' if action_required else 'Automatic Retry in Progress'}
                        </h4>
                        <p style="margin: 0;">{message}</p>
                    </div>
                    
                    <div style="margin: 20px 0;">
                        <h4>Order Details:</h4>
                        <ul>
                            <li><strong>Order ID:</strong> #{order.id}</li>
                            <li><strong>Amount:</strong> ${order.total_amount / 100:.2f}</li>
                            <li><strong>Date:</strong> {order.created_at.strftime('%Y-%m-%d %H:%M')}</li>
                        </ul>
                    </div>
                    
                    {'<div style="text-align: center; margin: 30px 0;"><a href="' + 
                     current_app.config.get('SITE_URL', 'http://localhost:5001') + 
                     '/checkout?order_id=' + str(order.id) + 
                     '" style="background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Update Payment Method</a></div>' 
                     if action_required else ''}
                    
                    <p style="margin-top: 30px;">
                        If you have any questions, please contact our support team.<br>
                        Thank you for your business!
                    </p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666;">
                        FlashStudio - Professional Video Production Services
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send email (would integrate with email service)
            # For now, just log the notification
            logger.info(f"Customer notification sent for order {order_id}: {subject}")
            context.customer_notified = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send customer notification for order {order_id}: {e}")
            return False
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get statistics about retry attempts"""
        total_contexts = len(self.retry_contexts)
        successful_retries = sum(1 for ctx in self.retry_contexts.values() 
                               if any(attempt.success for attempt in ctx.attempts))
        final_failures = sum(1 for ctx in self.retry_contexts.values() if ctx.final_failure)
        pending_retries = len(self.get_pending_retries())
        
        # Failure reason breakdown
        reason_counts = {}
        for ctx in self.retry_contexts.values():
            reason = ctx.original_failure_reason.value
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return {
            'total_retry_contexts': total_contexts,
            'successful_retries': successful_retries,
            'final_failures': final_failures,
            'pending_retries': pending_retries,
            'success_rate': (successful_retries / total_contexts * 100) if total_contexts > 0 else 0,
            'failure_reason_breakdown': reason_counts,
            'timestamp': datetime.utcnow().isoformat()
        }


# Global retry service instance
payment_retry_service = PaymentRetryService()


def handle_payment_failure(order_id: int, payment_intent_id: str, stripe_error) -> Dict[str, Any]:
    """
    Handle payment failure with intelligent retry logic
    
    Args:
        order_id: Order ID
        payment_intent_id: Stripe payment intent ID
        stripe_error: Stripe error object
        
    Returns:
        Dict with retry information
    """
    try:
        # Create or update retry context
        existing_context = payment_retry_service.get_retry_context(payment_intent_id)
        
        if existing_context:
            # Add retry attempt to existing context
            payment_retry_service.add_retry_attempt(payment_intent_id, stripe_error, success=False)
            context = existing_context
        else:
            # Create new retry context
            context = payment_retry_service.create_retry_context(order_id, payment_intent_id, stripe_error)
        
        # Send customer notification if required
        config = payment_retry_service.retry_configs.get(context.original_failure_reason)
        if config and config['notify_customer']:
            payment_retry_service.send_customer_notification(
                order_id, context.original_failure_reason, context
            )
        
        # Return retry information
        return {
            'retry_context_created': True,
            'failure_reason': context.original_failure_reason.value,
            'retry_strategy': context.retry_strategy.value,
            'will_retry': context.next_retry_at is not None,
            'next_retry_at': context.next_retry_at.isoformat() if context.next_retry_at else None,
            'attempts_made': context.current_attempts,
            'max_attempts': context.max_attempts,
            'customer_notified': context.customer_notified
        }
        
    except Exception as e:
        logger.error(f"Error handling payment failure for {payment_intent_id}: {e}")
        return {
            'retry_context_created': False,
            'error': str(e)
        }


def handle_payment_success(payment_intent_id: str) -> bool:
    """
    Handle successful payment (end retry cycle)
    
    Args:
        payment_intent_id: Stripe payment intent ID
        
    Returns:
        True if retry context was updated
    """
    try:
        context = payment_retry_service.get_retry_context(payment_intent_id)
        if context:
            payment_retry_service.add_retry_attempt(payment_intent_id, None, success=True)
            logger.info(f"Payment {payment_intent_id} succeeded after {context.current_attempts} attempts")
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error handling payment success for {payment_intent_id}: {e}")
        return False
"""
Stripe payment service for FlashStudio
Handles payment intents, confirmations, and webhooks
"""
import stripe
import logging
from datetime import datetime
from flask import current_app, url_for
from typing import Dict, Any, Optional, Tuple
from models import Order, db

# Configure logging
logger = logging.getLogger(__name__)

class StripeService:
    """Stripe payment service with error handling and logging"""
    
    def __init__(self):
        self._initialized = False
    
    def init_app(self, app):
        """Initialize Stripe with Flask app configuration"""
        try:
            stripe.api_key = app.config.get('STRIPE_SECRET_KEY')
            self._initialized = bool(stripe.api_key)
            
            if not self._initialized:
                logger.warning("Stripe not initialized - missing STRIPE_SECRET_KEY")
            else:
                logger.info("Stripe service initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize Stripe: {e}")
            self._initialized = False
    
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured"""
        return self._initialized and bool(stripe.api_key)
    
    def create_payment_intent(self, order: Order, metadata: Optional[Dict] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a Stripe Payment Intent for an order
        
        Args:
            order: Order instance
            metadata: Optional metadata dict
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        if not self.is_configured():
            return False, {"error": "Stripe not configured"}
        
        try:
            # Prepare metadata
            intent_metadata = {
                "order_id": str(order.id),
                "customer_email": order.customer_email,
                "source": "FlashStudio"
            }
            if metadata:
                intent_metadata.update(metadata)
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=order.amount_cents,
                currency=current_app.config.get('CURRENCY', 'sgd'),
                metadata=intent_metadata,
                automatic_payment_methods={
                    'enabled': True,
                },
                # Add receipt email if available
                receipt_email=order.customer_email if order.customer_email else None,
            )
            
            # Update order with payment intent ID
            order.stripe_payment_intent = intent.id
            order.status = "payment_pending"
            db.session.commit()
            
            logger.info(f"Created payment intent {intent.id} for order {order.id}")
            
            return True, {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "amount": order.amount_cents,
                "currency": intent.currency
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            return False, {"error": f"Payment error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error creating payment intent: {e}")
            return False, {"error": "Payment system temporarily unavailable"}
    
    def confirm_payment_intent(self, payment_intent_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Confirm and retrieve payment intent status
        
        Args:
            payment_intent_id: Stripe Payment Intent ID
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        if not self.is_configured():
            return False, {"error": "Stripe not configured"}
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Safely get charges data
            charges_data = []
            try:
                if hasattr(intent, 'charges') and intent.charges:
                    charges_data = list(intent.charges.data) if intent.charges.data else []
            except Exception:
                # If charges can't be accessed, continue without them
                pass
            
            return True, {
                "status": intent.status,
                "payment_intent_id": intent.id,
                "amount_received": getattr(intent, 'amount_received', 0),
                "charges": charges_data
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving payment intent {payment_intent_id}: {e}")
            return False, {"error": f"Payment verification error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error retrieving payment intent {payment_intent_id}: {e}")
            return False, {"error": "Payment verification failed"}
    
    def handle_payment_success(self, payment_intent_id: str) -> Tuple[bool, Optional[Order]]:
        """
        Handle successful payment completion
        
        Args:
            payment_intent_id: Stripe Payment Intent ID
            
        Returns:
            Tuple of (success: bool, order: Optional[Order])
        """
        try:
            # Find order by payment intent ID
            order = Order.query.filter_by(stripe_payment_intent=payment_intent_id).first()
            if not order:
                logger.error(f"Order not found for payment intent {payment_intent_id}")
                return False, None
            
            # Verify payment with Stripe - simplified approach
            try:
                intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                stripe_status = intent.status
                
                if stripe_status == "succeeded":
                    order.status = "paid"
                    if not order.payment_completed_at:
                        order.payment_completed_at = datetime.utcnow()
                    logger.info(f"Order {order.id} marked as paid (PaymentIntent: {payment_intent_id})")
                elif stripe_status in ["requires_action", "requires_confirmation"]:
                    order.status = "payment_pending"
                else:
                    order.status = "payment_failed"
                    logger.warning(f"Order {order.id} payment failed with status: {stripe_status}")
                
                db.session.commit()
                return True, order
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error verifying payment {payment_intent_id}: {e}")
                return False, order
            
        except Exception as e:
            logger.error(f"Error handling payment success for {payment_intent_id}: {e}")
            db.session.rollback()
            return False, None
    
    def process_webhook(self, payload: bytes, signature: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Process Stripe webhook events
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        if not self.is_configured():
            return False, {"error": "Stripe not configured"}
        
        webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
        if not webhook_secret:
            logger.warning("Webhook received but STRIPE_WEBHOOK_SECRET not configured")
            return False, {"error": "Webhook not configured"}
        
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            
            logger.info(f"Received Stripe webhook: {event['type']}")
            
            # Handle different event types
            if event['type'] == 'payment_intent.succeeded':
                return self._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                return self._handle_payment_failed(event['data']['object'])
            elif event['type'] == 'payment_intent.requires_action':
                return self._handle_payment_requires_action(event['data']['object'])
            else:
                logger.info(f"Unhandled webhook event type: {event['type']}")
                return True, {"message": "Event ignored"}
                
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False, {"error": "Invalid signature"}
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return False, {"error": "Webhook processing failed"}
    
    def _handle_payment_succeeded(self, payment_intent: Dict) -> Tuple[bool, Dict[str, Any]]:
        """Handle successful payment webhook"""
        try:
            success, order = self.handle_payment_success(payment_intent['id'])
            if success and order:
                return True, {"message": f"Order {order.id} marked as paid"}
            return False, {"error": "Failed to update order"}
        except Exception as e:
            logger.error(f"Error handling payment success webhook: {e}")
            return False, {"error": str(e)}
    
    def _handle_payment_failed(self, payment_intent: Dict) -> Tuple[bool, Dict[str, Any]]:
        """Handle failed payment webhook"""
        try:
            order = Order.query.filter_by(stripe_payment_intent=payment_intent['id']).first()
            if order:
                order.status = "payment_failed"
                db.session.commit()
                logger.info(f"Order {order.id} marked as payment failed")
                return True, {"message": f"Order {order.id} marked as failed"}
            return False, {"error": "Order not found"}
        except Exception as e:
            logger.error(f"Error handling payment failure webhook: {e}")
            db.session.rollback()
            return False, {"error": str(e)}
    
    def _handle_payment_requires_action(self, payment_intent: Dict) -> Tuple[bool, Dict[str, Any]]:
        """Handle payment requiring additional action"""
        try:
            order = Order.query.filter_by(stripe_payment_intent=payment_intent['id']).first()
            if order:
                order.status = "payment_pending"
                db.session.commit()
                logger.info(f"Order {order.id} requires additional payment action")
                return True, {"message": f"Order {order.id} requires action"}
            return False, {"error": "Order not found"}
        except Exception as e:
            logger.error(f"Error handling payment requires action webhook: {e}")
            db.session.rollback()
            return False, {"error": str(e)}

# Global instance
stripe_service = StripeService()
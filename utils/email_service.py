"""
Email service utility for FlashStudio
Integrates with Azure Functions EmailNotifications service
"""
import requests
import logging
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)


class EmailService:
    """Service to handle email notifications via Azure Functions"""
    
    @staticmethod
    def get_function_url():
        """Get the Azure Function URL from configuration"""
        return current_app.config.get(
            'EMAIL_FUNCTION_URL', 
            'https://flashstudio-functions.azurewebsites.net/api/EmailNotifications'
        )
    
    @staticmethod
    def send_order_confirmation(order):
        """
        Send order confirmation email to customer
        
        Args:
            order: Order object with customer details and items
            
        Returns:
            dict: Response from email service
        """
        try:
            # Prepare order items data
            items = []
            for item in order.items:
                items.append({
                    'name': item.product.title if item.product else 'Product',
                    'price': f"{item.unit_price_cents / 100:.2f}",
                    'quantity': item.quantity,
                    'total': f"{(item.unit_price_cents * item.quantity) / 100:.2f}"
                })
            
            # Prepare email data
            email_data = {
                'type': 'order_confirmation',
                'to': order.customer_email,
                'name': order.user.email.split('@')[0] if order.user else 'Valued Customer',  # Use email prefix as name
                'order_id': f"ORD{order.id:05d}",
                'total_amount': f"{order.amount_cents / 100:.2f}",
                'currency': 'S$',
                'items': items,
                'order_date': order.created_at.strftime('%B %d, %Y') if order.created_at else datetime.now().strftime('%B %d, %Y')
            }
            
            # Send email via Azure Function
            function_url = EmailService.get_function_url()
            
            # If no function URL configured, log and return success (for local development)
            if not function_url or 'localhost' in function_url:
                logger.warning("Email function URL not configured, skipping email send")
                return {
                    'success': True,
                    'message': 'Email service not configured (development mode)',
                    'local_dev': True
                }
            
            response = requests.post(
                function_url,
                json=email_data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Order confirmation email sent successfully to {order.customer_email}")
                return result
            else:
                logger.error(f"Email service returned status {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'Email service error: {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            logger.error("Email service timeout")
            return {
                'success': False,
                'error': 'Email service timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Email service request failed: {e}")
            return {
                'success': False,
                'error': f'Email service unavailable: {e}'
            }
        except Exception as e:
            logger.error(f"Unexpected error in email service: {e}")
            return {
                'success': False,
                'error': f'Email service error: {e}'
            }
    
    @staticmethod
    def send_payment_failure_notification(order, error_message=None):
        """
        Send notification about payment failure
        
        Args:
            order: Order object
            error_message: Optional error details
            
        Returns:
            dict: Response from email service
        """
        try:
            email_data = {
                'type': 'custom',
                'to': order.customer_email,
                'name': order.user.email.split('@')[0] if order.user else 'Customer',
                'subject': f'Payment Failed for Order #{order.id:05d}',
                'message': f"""
                <p>We were unable to process your payment for order <strong>#{order.id:05d}</strong>.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p><strong>Order Details:</strong></p>
                    <p>Amount: S$ {order.amount_cents / 100:.2f}</p>
                    <p>Date: {order.created_at.strftime('%B %d, %Y') if order.created_at else 'Today'}</p>
                </div>
                
                <p>Please try again or contact our support team if you continue to experience issues.</p>
                
                <p><a href="https://flashstudio.com/cart" style="color: #007bff;">Try Payment Again</a></p>
                """
            }
            
            function_url = EmailService.get_function_url()
            
            if not function_url or 'localhost' in function_url:
                logger.warning("Email function URL not configured, skipping failure notification")
                return {'success': True, 'local_dev': True}
            
            response = requests.post(function_url, json=email_data, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Payment failure notification sent to {order.customer_email}")
                return response.json()
            else:
                logger.error(f"Failed to send payment failure notification: {response.status_code}")
                return {'success': False, 'error': 'Failed to send notification'}
                
        except Exception as e:
            logger.error(f"Error sending payment failure notification: {e}")
            return {'success': False, 'error': str(e)}


def send_order_confirmation_email(order):
    """
    Convenience function to send order confirmation email
    
    Args:
        order: Order object
        
    Returns:
        dict: Response from email service
    """
    return EmailService.send_order_confirmation(order)


def send_payment_failure_email(order, error_message=None):
    """
    Convenience function to send payment failure notification
    
    Args:
        order: Order object  
        error_message: Optional error details
        
    Returns:
        dict: Response from email service
    """
    return EmailService.send_payment_failure_notification(order, error_message)
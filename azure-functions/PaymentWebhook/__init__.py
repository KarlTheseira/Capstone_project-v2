import azure.functions as func
import logging
import json
import stripe
import os
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to handle Stripe payment webhooks
    
    This function processes Stripe webhook events for payment confirmations,
    failures, and other payment-related events.
    """
    
    logging.info('🎯 Payment webhook triggered')
    
    try:
        # Configure Stripe with secret key
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        
        # Get webhook payload and signature
        payload = req.get_body()
        sig_header = req.headers.get('stripe-signature')
        endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        if not endpoint_secret:
            logging.error("❌ STRIPE_WEBHOOK_SECRET not configured")
            return func.HttpResponse(
                "Webhook secret not configured", 
                status_code=500
            )
        
        # Verify webhook signature (important for security!)
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            logging.error(f"❌ Invalid payload: {e}")
            return func.HttpResponse("Invalid payload", status_code=400)
        except stripe.error.SignatureVerificationError as e:
            logging.error(f"❌ Invalid signature: {e}")
            return func.HttpResponse("Invalid signature", status_code=400)
        
        # Process different event types
        event_type = event['type']
        logging.info(f"📧 Processing event: {event_type}")
        
        if event_type == 'payment_intent.succeeded':
            return handle_payment_success(event['data']['object'])
            
        elif event_type == 'payment_intent.payment_failed':
            return handle_payment_failure(event['data']['object'])
            
        elif event_type == 'checkout.session.completed':
            return handle_checkout_completed(event['data']['object'])
            
        else:
            logging.info(f"ℹ️  Unhandled event type: {event_type}")
            return func.HttpResponse(
                json.dumps({"status": "received", "event_type": event_type}),
                status_code=200,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"💥 Error processing webhook: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


def handle_payment_success(payment_intent):
    """Handle successful payment"""
    
    payment_id = payment_intent['id']
    amount = payment_intent['amount'] / 100  # Convert from cents
    currency = payment_intent['currency'].upper()
    
    logging.info(f"✅ Payment succeeded: {payment_id} - {currency} {amount}")
    
    try:
        # Extract customer info from metadata
        customer_email = payment_intent.get('receipt_email')
        order_id = payment_intent.get('metadata', {}).get('order_id')
        
        # Here you would typically:
        # 1. Update order status in your database
        # 2. Send confirmation email to customer
        # 3. Trigger fulfillment process
        # 4. Update inventory
        
        # For now, we'll log the success and return
        logging.info(f"📧 Order {order_id} confirmed for {customer_email}")
        
        # You could call your main app's API here
        main_app_url = os.environ.get('MAIN_APP_URL')
        if main_app_url and order_id:
            # Example API call to update order status
            # requests.post(f"{main_app_url}/api/orders/{order_id}/confirm", 
            #               json={"payment_intent_id": payment_id})
            pass
        
        return func.HttpResponse(
            json.dumps({
                "status": "success", 
                "message": "Payment processed successfully",
                "payment_id": payment_id,
                "amount": amount,
                "currency": currency
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"💥 Error handling successful payment: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to process successful payment"}),
            status_code=500,
            mimetype="application/json"
        )


def handle_payment_failure(payment_intent):
    """Handle failed payment"""
    
    payment_id = payment_intent['id']
    failure_reason = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
    
    logging.warning(f"❌ Payment failed: {payment_id} - {failure_reason}")
    
    try:
        # Extract order info
        order_id = payment_intent.get('metadata', {}).get('order_id')
        customer_email = payment_intent.get('receipt_email')
        
        # Here you would:
        # 1. Mark order as failed in database
        # 2. Send failure notification to customer
        # 3. Optionally trigger retry logic
        # 4. Log for admin review
        
        logging.info(f"📧 Payment failure processed for order {order_id}")
        
        return func.HttpResponse(
            json.dumps({
                "status": "handled", 
                "message": "Payment failure processed",
                "payment_id": payment_id,
                "failure_reason": failure_reason
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"💥 Error handling payment failure: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to process payment failure"}),
            status_code=500,
            mimetype="application/json"
        )


def handle_checkout_completed(session):
    """Handle completed checkout session"""
    
    session_id = session['id']
    customer_email = session.get('customer_details', {}).get('email')
    
    logging.info(f"🛒 Checkout completed: {session_id} for {customer_email}")
    
    try:
        # Process checkout completion
        # This could trigger welcome emails, account setup, etc.
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": "Checkout completion processed",
                "session_id": session_id
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"💥 Error handling checkout completion: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to process checkout completion"}),
            status_code=500,
            mimetype="application/json"
        )
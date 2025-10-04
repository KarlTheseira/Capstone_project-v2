"""
Payment routes for FlashStudio
Handles Stripe payment intents, confirmations, and webhooks
"""
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, session
from models import Order, db
from utils.stripe_service import stripe_service
from utils.rate_limiting import rate_limit
from utils.payment_retry import handle_payment_failure, handle_payment_success
import logging

logger = logging.getLogger(__name__)

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

@payment_bp.route('/create-intent', methods=['POST'])
@rate_limit('payment_intent')
def create_intent():
    """Create a Stripe Payment Intent for checkout"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'error': 'Order ID required'}), 400
        
        # Get the order
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check if order belongs to current user (if logged in)
        if session.get('user_id') and order.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Create payment intent
        success, result = stripe_service.create_payment_intent(order)
        
        if success:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating payment intent: {e}")
        return jsonify({'error': 'Payment system error'}), 500

@payment_bp.route('/confirm', methods=['POST'])
@rate_limit('payment_confirm')
def confirm_payment():
    """Confirm payment completion"""
    try:
        data = request.get_json()
        payment_intent_id = data.get('payment_intent_id')
        
        if not payment_intent_id:
            return jsonify({'error': 'Payment Intent ID required'}), 400
        
        # Handle payment success
        success, order = stripe_service.handle_payment_success(payment_intent_id)
        
        if success and order:
            # Clear the cart on successful payment
            session.pop('cart', None)
            
            return jsonify({
                'success': True,
                'order_id': order.id,
                'redirect_url': url_for('payment.success', order_id=order.id)
            })
        else:
            return jsonify({'error': 'Payment confirmation failed'}), 400
            
    except Exception as e:
        logger.error(f"Error confirming payment: {e}")
        return jsonify({'error': 'Payment confirmation error'}), 500

@payment_bp.route('/success/<int:order_id>')
def success(order_id):
    """Payment success page"""
    order = db.session.get(Order, order_id)
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('public.index'))
    
    # Check if order belongs to current user (if logged in)
    if session.get('user_id') and order.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('public.index'))
    
    return render_template('payment_success.html', order=order)

@payment_bp.route('/cancel')
def cancel():
    """Payment cancelled page"""
    flash('Payment was cancelled. Your cart has been preserved.', 'info')
    return redirect(url_for('public.cart'))

@payment_bp.route('/status/<payment_intent_id>')
def payment_status(payment_intent_id):
    """Get payment status (for AJAX polling)"""
    try:
        success, result = stripe_service.confirm_payment_intent(payment_intent_id)
        
        if success:
            return jsonify({
                'status': result['status'],
                'payment_intent_id': payment_intent_id
            })
        else:
            return jsonify({'error': 'Status check failed'}), 400
            
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return jsonify({'error': 'Status check error'}), 500

# Webhook endpoint
@payment_bp.route('/webhook', methods=['POST'])
@rate_limit('webhook')
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.get_data()
        signature = request.headers.get('Stripe-Signature')
        
        if not signature:
            logger.warning("Webhook received without signature")
            return jsonify({'error': 'Missing signature'}), 400
        
        # Process webhook
        success, result = stripe_service.process_webhook(payload, signature)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            logger.error(f"Webhook processing failed: {result}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500
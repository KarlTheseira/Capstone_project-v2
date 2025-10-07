from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, current_app
from sqlalchemy.exc import SQLAlchemyError
from models import db, Order, OrderItem, Product, User
from utils.dummy_payments import provider as dummy_provider
from utils.email_service import send_order_confirmation_email, send_payment_failure_email
import os
import stripe
import logging
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')


def using_dummy():
	return os.getenv('PAYMENTS_PROVIDER', 'dummy').lower() == 'dummy'


class StripeService:
    """Service class to handle Stripe operations"""
    
    @staticmethod
    def initialize_stripe():
        """Initialize Stripe with API keys"""
        try:
            stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Stripe: {e}")
            return False
    
    @staticmethod
    def create_checkout_session(items, customer_email=None, order_id=None):
        """Create a Stripe checkout session (fake mode for testing)"""
        try:
            if not StripeService.initialize_stripe():
                raise Exception("Stripe not properly configured")
            
            # For fake/test mode, simulate the session creation
            if current_app.config.get('STRIPE_SECRET_KEY', '').startswith('sk_test_fake'):
                # Return a fake session for testing
                return {
                    'id': f'cs_test_fake_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                    'url': f"/payment/fake-checkout?session_id=cs_test_fake_{datetime.now().strftime('%Y%m%d%H%M%S')}&order_id={order_id}"
                }
            
            # Convert cart items to Stripe line items (for real Stripe)
            line_items = []
            for item in items:
                line_items.append({
                    'price_data': {
                        'currency': current_app.config.get('CURRENCY', 'sgd'),
                        'product_data': {
                            'name': item['title'],
                            'description': f"Size: {item.get('size', 'Standard')} | Frame: {item.get('frame', 'No frame')}",
                        },
                        'unit_amount': item['unit_price_cents'],
                    },
                    'quantity': item['qty'],
                })
            
            # For now, return fake session (replace with real Stripe when ready)
            return {
                'id': f'cs_test_fake_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'url': f"/payment/fake-checkout?session_id=cs_test_fake_{datetime.now().strftime('%Y%m%d%H%M%S')}&order_id={order_id}"
            }
            
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise e


@payment_bp.route('/create-intent', methods=['POST'])
def create_intent():
	"""Create a dummy payment intent and a provisional Order.
	Expected JSON:
	{
		"email": "customer@example.com",
		"currency": "usd", (optional)
		"items": [ {"product_id": 1, "quantity": 2}, ...]
	}
	"""
	if not using_dummy():
		return jsonify({'error': 'Only dummy provider implemented'}), 400

	data = request.get_json(force=True, silent=True) or {}
	email = data.get('email')
	items = data.get('items', [])
	currency = data.get('currency', 'usd')

	if not email or not items:
		return jsonify({'error': 'email and items are required'}), 400

	# Validate items and compute amount
	product_map = {}
	amount_cents = 0
	for item in items:
		pid = item.get('product_id')
		qty = int(item.get('quantity', 1))
		if not pid or qty <= 0:
			return jsonify({'error': f'invalid item spec {item}'}), 400
		product = Product.query.get(pid)
		if not product:
			return jsonify({'error': f'product {pid} not found'}), 404
		product_map[pid] = product
		amount_cents += product.price_cents * qty

	# Create dummy payment intent
	intent = dummy_provider.create_payment_intent(amount_cents, currency, metadata={'email': email})

	# Persist Order and OrderItems (status=created)
	order = Order(
		email=email,
		amount_cents=amount_cents,
		currency=currency,
		stripe_payment_intent=intent.id,  # reusing field name
		status='created'
	)
	db.session.add(order)
	db.session.flush()  # to get order.id

	for item in items:
		pid = item['product_id']
		qty = int(item.get('quantity', 1))
		product = product_map[pid]
		db.session.add(OrderItem(
			order_id=order.id,
			product_id=pid,
			quantity=qty,
			unit_price_cents=product.price_cents
		))

	try:
		db.session.commit()
	except SQLAlchemyError as e:
		db.session.rollback()
		return jsonify({'error': 'db_error', 'details': str(e)}), 500

	return jsonify({
		'payment_intent': intent.to_dict(),
		'order_id': order.id,
		'amount_cents': amount_cents,
		'currency': currency
	}), 201


@payment_bp.route('/confirm', methods=['POST'])
def confirm_intent():
	if not using_dummy():
		return jsonify({'error': 'Only dummy provider implemented'}), 400

	data = request.get_json(force=True, silent=True) or {}
	intent_id = data.get('payment_intent_id')
	if not intent_id:
		return jsonify({'error': 'payment_intent_id required'}), 400

	intent = dummy_provider.confirm(intent_id)
	if not intent:
		return jsonify({'error': 'intent_not_found'}), 404

	# Update associated order status to paid
	order = Order.query.filter_by(stripe_payment_intent=intent_id).first()
	if order and order.status != 'paid':
		order.status = 'paid'
		try:
			db.session.commit()
		except SQLAlchemyError as e:
			db.session.rollback()
			return jsonify({'error': 'db_error', 'details': str(e)}), 500

	return jsonify({'payment_intent': intent.to_dict(), 'order_id': order.id if order else None})


@payment_bp.route('/intent/<intent_id>', methods=['GET'])
def get_intent(intent_id):
	if not using_dummy():
		return jsonify({'error': 'Only dummy provider implemented'}), 400

	intent = dummy_provider.retrieve(intent_id)
	if not intent:
		return jsonify({'error': 'intent_not_found'}), 404

	return jsonify({'payment_intent': intent.to_dict()})


# New Stripe Checkout Routes
@payment_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe checkout session from cart"""
    try:
        # Get cart from session
        cart_raw = session.get("cart", [])
        if not cart_raw:
            return jsonify({'error': 'Cart is empty'}), 400

        # Process cart items
        items = []
        total = 0
        
        # Size and frame options (should match your existing constants)
        SIZE_OPTIONS = {
            "20cm x 30cm": 0,
            "30cm x 40cm": 2000,  # +$20.00
            "40cm x 50cm": 4000,  # +$40.00
        }
        
        FRAME_OPTIONS = {
            "No frame": 0,
            "Basic wooden frame": 1500,  # +$15.00
            "Premium metal frame": 3000,  # +$30.00
        }

        for idx, it in enumerate(cart_raw):
            pid = it.get("product_id") or it.get("id")
            qty = int(it.get("qty", 1))
            size = it.get("size", "20cm x 30cm")
            frame = it.get("frame", "No frame")

            p = Product.query.get(pid)
            if not p:
                continue

            unit = it.get("unit_price_cents")
            if unit is None:
                size_add = int(SIZE_OPTIONS.get(size, 0))
                frame_add = int(FRAME_OPTIONS.get(frame, 0))
                unit = int(p.price_cents) + size_add + frame_add
                it["unit_price_cents"] = unit

            subtotal = int(unit) * qty
            total += subtotal

            items.append({
                "idx": idx,
                "title": p.title,
                "size": size,
                "frame": frame,
                "qty": qty,
                "unit_price_cents": unit,
                "subtotal_cents": subtotal,
            })

        # Get customer email
        customer_email = None
        if session.get("user_id"):
            user = db.session.get(User, session["user_id"])
            if user:
                customer_email = user.email

        # Create pending order
        order = Order(
            email=customer_email or "guest@flashstudio.com",
            amount_cents=total,
            currency=current_app.config.get('CURRENCY', 'sgd'),
            status="pending"
        )
        
        if session.get("user_id"):
            order.user_id = session["user_id"]
        
        db.session.add(order)
        db.session.flush()

        # Create order items
        for idx, item in enumerate(items):
            cart_item = cart_raw[idx]
            product_id = cart_item.get("product_id") or cart_item.get("id")
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=item["qty"],
                unit_price_cents=item["unit_price_cents"]
            )
            db.session.add(order_item)
        
        db.session.commit()

        # Create Stripe checkout session
        checkout_session = StripeService.create_checkout_session(
            items=items,
            customer_email=customer_email,
            order_id=order.id
        )

        # Store order ID in session for later reference
        session['pending_order_id'] = order.id
        session.modified = True

        return jsonify({
            'checkout_url': checkout_session['url'],
            'session_id': checkout_session['id']
        })

    except Exception as e:
        logger.error(f"Error in create_checkout_session: {e}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({'error': 'Failed to create checkout session'}), 500


@payment_bp.route('/fake-checkout')
def fake_checkout():
    """Fake Stripe checkout page for testing"""
    session_id = request.args.get('session_id')
    order_id = request.args.get('order_id')
    
    if not session_id:
        flash("Invalid checkout session", "danger")
        return redirect(url_for('public.cart'))
    
    # Get order
    order = None
    if order_id:
        order = db.session.get(Order, int(order_id))
    else:
        # Try from session
        pending_order_id = session.get('pending_order_id')
        if pending_order_id:
            order = db.session.get(Order, pending_order_id)
    
    if not order:
        flash("Order not found", "danger")
        return redirect(url_for('public.cart'))
    
    return render_template('payment/fake_checkout.html', 
                         order=order, 
                         session_id=session_id)


@payment_bp.route('/fake-checkout/complete', methods=['POST'])
def complete_fake_checkout():
    """Complete the fake checkout (simulate payment outcomes)"""
    try:
        order_id = request.form.get('order_id')
        if not order_id:
            flash("No order specified", "warning")
            return redirect(url_for('public.cart'))
        
        order = db.session.get(Order, int(order_id))
        if not order:
            flash("Order not found", "danger")
            return redirect(url_for('public.cart'))
        
        # Get payment outcome choice
        payment_choice = request.form.get('payment_choice', 'success')
        
        if payment_choice == 'success':
            # Successful payment
            order.status = 'paid'
            order.stripe_payment_intent = f'pi_fake_{datetime.now().strftime("%Y%m%d%H%M%S")}'
            db.session.commit()
            
            # Send confirmation email (don't let email failures break the payment process)
            email_sent = False
            try:
                email_result = send_order_confirmation_email(order)
                if email_result.get('success'):
                    logger.info(f"Order confirmation email sent for order {order.id}")
                    email_sent = True
                else:
                    logger.warning(f"Failed to send confirmation email for order {order.id}: {email_result.get('error')}")
            except Exception as e:
                logger.error(f"Error sending confirmation email for order {order.id}: {e}")
                logger.error(traceback.format_exc())
                # Continue processing - email failure shouldn't break the payment flow
            
            # Clear cart and session
            session.pop('cart', None)
            session.pop('pending_order_id', None)
            session.modified = True
            
            # Update success message based on email status
            if email_sent:
                flash("Payment successful! A confirmation email has been sent to your email address.", "success")
            else:
                flash("Payment successful! Please save your order number for reference. If you don't receive a confirmation email, please contact support.", "success")
            
            return redirect(url_for('payment.success', session_id=f'cs_fake_{order.id}'))
            
        elif payment_choice == 'failure':
            # Failed payment
            order.status = 'failed'
            db.session.commit()
            
            # Send failure notification email
            try:
                email_result = send_payment_failure_email(order, "Payment was declined by the card issuer")
                if email_result.get('success'):
                    logger.info(f"Payment failure notification sent for order {order.id}")
            except Exception as e:
                logger.error(f"Error sending payment failure notification: {e}")
            
            flash("Payment failed. Please check your payment details and try again.", "danger")
            return redirect(url_for('payment.cancel'))
            
        else:
            # Cancelled payment
            order.status = 'cancelled'
            db.session.commit()
            
            flash("Payment was cancelled. Your items are still in your cart.", "warning")
            return redirect(url_for('payment.cancel'))
            
    except Exception as e:
        logger.error(f"Error completing fake checkout: {e}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        flash("An error occurred during payment processing. Please try again.", "danger")
        return redirect(url_for('payment.cancel'))


@payment_bp.route('/success')
def success():
    """Payment success page"""
    session_id = request.args.get('session_id')
    
    # Try to find the order
    order = None
    if session_id and 'fake' in session_id:
        # Extract order ID from fake session
        try:
            order_id = int(session_id.split('_')[-1])
            order = db.session.get(Order, order_id)
        except (ValueError, IndexError):
            logger.warning(f"Could not extract order ID from session_id: {session_id}")
    
    if not order:
        # Try to get from session as fallback
        pending_order_id = session.get('pending_order_id')
        if pending_order_id:
            order = db.session.get(Order, pending_order_id)
            logger.info(f"Found order from session: {order.id}" if order else "No order found in session")
    
    if order and order.status == 'paid':
        # Ensure order items are loaded (for template display)
        db.session.refresh(order)
        logger.info(f"Displaying success page for paid order {order.id}")
        return render_template('payment/success.html', order=order)
    elif order:
        logger.warning(f"Order {order.id} found but status is {order.status}, not paid")
        flash(f"Order found but payment status is {order.status}. Please contact support if you believe this is an error.", "warning")
        return redirect(url_for('public.shop'))
    else:
        logger.warning("No order found for success page")
        flash("Payment confirmation not found. Please check your email for order details or contact support.", "warning")
        return redirect(url_for('public.shop'))


@payment_bp.route('/cancel')
def cancel():
    """Payment cancelled/failed page"""
    return render_template('payment/cancel.html')

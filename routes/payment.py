from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from models import db, Order, OrderItem, Product
from utils.dummy_payments import provider as dummy_provider
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from models import db, Order, OrderItem, Product
from utils.dummy_payments import provider as dummy_provider
import os

payment_bp = Blueprint('payment', __name__, url_prefix='/api/payments')


def using_dummy():
	return os.getenv('PAYMENTS_PROVIDER', 'dummy').lower() == 'dummy'


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

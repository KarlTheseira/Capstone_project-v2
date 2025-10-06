import json
from app import app, db, init_db
from models import Product, Order


def setup_module(module):
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            p = Product(title='Test Product', description='Desc', price_cents=1234, media_key='x', stock=10)
            db.session.add(p)
            db.session.commit()

def test_create_and_confirm_intent():
    client = app.test_client()
    with app.app_context():
        product = Product.query.first()
        payload = {
            'email': 'buyer@example.com',
            'items': [ {'product_id': product.id, 'quantity': 2} ],
            'currency': 'usd'
        }
        resp = client.post('/api/payments/create-intent', data=json.dumps(payload), content_type='application/json')
        assert resp.status_code == 201, resp.data
        data = resp.get_json()
        intent = data['payment_intent']
        assert intent['status'] == 'requires_confirmation'
        order_id = data['order_id']
        order = Order.query.get(order_id)
        assert order.amount_cents == product.price_cents * 2
        # confirm
        c_resp = client.post('/api/payments/confirm', data=json.dumps({'payment_intent_id': intent['id']}), content_type='application/json')
        assert c_resp.status_code == 200
        c_data = c_resp.get_json()
        assert c_data['payment_intent']['status'] == 'succeeded'
        order = Order.query.get(order_id)
        assert order.status == 'paid'

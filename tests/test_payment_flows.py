"""
Comprehensive Payment Flow Test Suite for FlashStudio
Tests all payment scenarios including success, failure, webhooks, and edge cases
"""
import unittest
import json
from unittest.mock import patch, Mock, MagicMock
from flask import Flask
from app import app
from models import db, User, Product, Order, OrderItem
from utils.stripe_service import stripe_service
import stripe
from datetime import datetime, timedelta

class PaymentFlowTestCase(unittest.TestCase):
    """Base test case for payment flow testing"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['STRIPE_SECRET_KEY'] = 'sk_test_fake_key'
        self.app.config['STRIPE_PUBLISHABLE_KEY'] = 'pk_test_fake_key'
        
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Create database tables
        db.create_all()
        
        # Create test data
        self.create_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def create_test_data(self):
        """Create test products and users"""
        # Test user
        self.test_user = User(
            email='test@flashstudio.com',
            name='Test User',
            phone='123-456-7890'
        )
        db.session.add(self.test_user)
        
        # Test products
        self.test_product = Product(
            name='Test Video Package',
            description='Test video editing service',
            price=10000,  # $100.00 in cents
            category='video',
            stock=10
        )
        db.session.add(self.test_product)
        
        db.session.commit()
        
        # Test order
        self.test_order = Order(
            user_id=self.test_user.id,
            total_amount=10000,
            status='pending'
        )
        db.session.add(self.test_order)
        db.session.commit()
        
        # Test order item
        self.test_order_item = OrderItem(
            order_id=self.test_order.id,
            product_id=self.test_product.id,
            quantity=1,
            price=10000
        )
        db.session.add(self.test_order_item)
        db.session.commit()


class TestPaymentIntentCreation(PaymentFlowTestCase):
    """Test payment intent creation and validation"""
    
    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_success(self, mock_stripe_create):
        """Test successful payment intent creation"""
        # Mock Stripe response
        mock_intent = Mock()
        mock_intent.id = 'pi_test_123'
        mock_intent.client_secret = 'pi_test_123_secret'
        mock_intent.amount = 10000
        mock_intent.currency = 'usd'
        mock_intent.status = 'requires_payment_method'
        mock_stripe_create.return_value = mock_intent
        
        # Make request
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        response = self.client.post('/payment/create-intent', 
                                  json={'order_id': self.test_order.id})
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('client_secret', data)
        self.assertEqual(data['amount'], 10000)
        
        # Verify Stripe was called with correct parameters
        mock_stripe_create.assert_called_once()
        call_args = mock_stripe_create.call_args[1]
        self.assertEqual(call_args['amount'], 10000)
        self.assertEqual(call_args['currency'], 'usd')
    
    def test_create_payment_intent_invalid_order(self):
        """Test payment intent creation with invalid order ID"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        response = self.client.post('/payment/create-intent', 
                                  json={'order_id': 99999})
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_create_payment_intent_unauthorized(self):
        """Test payment intent creation without authentication"""
        response = self.client.post('/payment/create-intent', 
                                  json={'order_id': self.test_order.id})
        
        self.assertEqual(response.status_code, 401)
    
    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_stripe_error(self, mock_stripe_create):
        """Test payment intent creation with Stripe error"""
        # Mock Stripe error
        mock_stripe_create.side_effect = stripe.error.InvalidRequestError(
            'Your card was declined.', 'card_declined'
        )
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        response = self.client.post('/payment/create-intent', 
                                  json={'order_id': self.test_order.id})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)


class TestPaymentConfirmation(PaymentFlowTestCase):
    """Test payment confirmation and order updates"""
    
    @patch('stripe.PaymentIntent.retrieve')
    def test_confirm_payment_success(self, mock_stripe_retrieve):
        """Test successful payment confirmation"""
        # Mock Stripe response
        mock_intent = Mock()
        mock_intent.id = 'pi_test_123'
        mock_intent.status = 'succeeded'
        mock_intent.amount = 10000
        mock_intent.charges = Mock()
        mock_intent.charges.data = [Mock()]
        mock_intent.charges.data[0].id = 'ch_test_123'
        mock_stripe_retrieve.return_value = mock_intent
        
        # Update order with payment intent ID
        self.test_order.stripe_payment_intent_id = 'pi_test_123'
        db.session.commit()
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        response = self.client.post('/payment/confirm', 
                                  json={'payment_intent_id': 'pi_test_123'})
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Check order status updated
        db.session.refresh(self.test_order)
        self.assertEqual(self.test_order.status, 'paid')
    
    @patch('stripe.PaymentIntent.retrieve')
    def test_confirm_payment_failed(self, mock_stripe_retrieve):
        """Test failed payment confirmation"""
        # Mock Stripe response
        mock_intent = Mock()
        mock_intent.id = 'pi_test_123'
        mock_intent.status = 'requires_payment_method'
        mock_intent.last_payment_error = Mock()
        mock_intent.last_payment_error.message = 'Your card was declined.'
        mock_stripe_retrieve.return_value = mock_intent
        
        # Update order with payment intent ID
        self.test_order.stripe_payment_intent_id = 'pi_test_123'
        db.session.commit()
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        response = self.client.post('/payment/confirm', 
                                  json={'payment_intent_id': 'pi_test_123'})
        
        # Assertions
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
        # Check order status
        db.session.refresh(self.test_order)
        self.assertEqual(self.test_order.status, 'failed')


class TestStripeWebhooks(PaymentFlowTestCase):
    """Test Stripe webhook handling"""
    
    def create_webhook_event(self, event_type, payment_intent_id):
        """Helper to create webhook event data"""
        return {
            'type': event_type,
            'data': {
                'object': {
                    'id': payment_intent_id,
                    'object': 'payment_intent',
                    'status': 'succeeded' if event_type == 'payment_intent.succeeded' else 'requires_payment_method',
                    'amount': 10000,
                    'currency': 'usd',
                    'charges': {
                        'data': [{'id': 'ch_test_123'}]
                    } if event_type == 'payment_intent.succeeded' else {'data': []}
                }
            }
        }
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_payment_succeeded(self, mock_construct_event):
        """Test successful payment webhook"""
        # Mock webhook event
        event_data = self.create_webhook_event('payment_intent.succeeded', 'pi_test_123')
        mock_construct_event.return_value = event_data
        
        # Update order with payment intent ID
        self.test_order.stripe_payment_intent_id = 'pi_test_123'
        db.session.commit()
        
        # Send webhook
        response = self.client.post('/payment/webhook',
                                  data=json.dumps(event_data),
                                  headers={
                                      'Content-Type': 'application/json',
                                      'Stripe-Signature': 'test_signature'
                                  })
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        
        # Check order updated
        db.session.refresh(self.test_order)
        self.assertEqual(self.test_order.status, 'completed')
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_payment_failed(self, mock_construct_event):
        """Test failed payment webhook"""
        # Mock webhook event
        event_data = self.create_webhook_event('payment_intent.payment_failed', 'pi_test_123')
        mock_construct_event.return_value = event_data
        
        # Update order with payment intent ID
        self.test_order.stripe_payment_intent_id = 'pi_test_123'
        db.session.commit()
        
        # Send webhook
        response = self.client.post('/payment/webhook',
                                  data=json.dumps(event_data),
                                  headers={
                                      'Content-Type': 'application/json',
                                      'Stripe-Signature': 'test_signature'
                                  })
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        
        # Check order updated
        db.session.refresh(self.test_order)
        self.assertEqual(self.test_order.status, 'failed')
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_invalid_signature(self, mock_construct_event):
        """Test webhook with invalid signature"""
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError(
            'Invalid signature', 'test_signature'
        )
        
        response = self.client.post('/payment/webhook',
                                  data=json.dumps({'test': 'data'}),
                                  headers={
                                      'Content-Type': 'application/json',
                                      'Stripe-Signature': 'invalid_signature'
                                  })
        
        self.assertEqual(response.status_code, 400)


class TestPaymentEdgeCases(PaymentFlowTestCase):
    """Test edge cases and error scenarios"""
    
    def test_duplicate_payment_intent_creation(self):
        """Test handling of duplicate payment intent requests"""
        # Set existing payment intent ID
        self.test_order.stripe_payment_intent_id = 'pi_existing_123'
        db.session.commit()
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        with patch('stripe.PaymentIntent.retrieve') as mock_retrieve:
            mock_intent = Mock()
            mock_intent.id = 'pi_existing_123'
            mock_intent.client_secret = 'pi_existing_123_secret'
            mock_intent.status = 'requires_payment_method'
            mock_retrieve.return_value = mock_intent
            
            response = self.client.post('/payment/create-intent',
                                      json={'order_id': self.test_order.id})
            
            # Should return existing intent
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['payment_intent_id'], 'pi_existing_123')
    
    def test_order_already_paid(self):
        """Test payment attempt on already paid order"""
        # Set order as already paid
        self.test_order.status = 'paid'
        db.session.commit()
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        response = self.client.post('/payment/create-intent',
                                  json={'order_id': self.test_order.id})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('already paid', data['error'].lower())
    
    def test_zero_amount_order(self):
        """Test payment with zero amount order"""
        # Create zero amount order
        zero_order = Order(
            user_id=self.test_user.id,
            total_amount=0,
            status='pending'
        )
        db.session.add(zero_order)
        db.session.commit()
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        response = self.client.post('/payment/create-intent',
                                  json={'order_id': zero_order.id})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('amount', data['error'].lower())


class TestPaymentIntegration(PaymentFlowTestCase):
    """Integration tests for complete payment flows"""
    
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_complete_payment_flow(self, mock_retrieve, mock_create):
        """Test complete payment flow from creation to confirmation"""
        # Mock payment intent creation
        mock_intent_created = Mock()
        mock_intent_created.id = 'pi_test_complete'
        mock_intent_created.client_secret = 'pi_test_complete_secret'
        mock_intent_created.amount = 10000
        mock_intent_created.currency = 'usd'
        mock_intent_created.status = 'requires_payment_method'
        mock_create.return_value = mock_intent_created
        
        # Mock payment intent retrieval (after payment)
        mock_intent_succeeded = Mock()
        mock_intent_succeeded.id = 'pi_test_complete'
        mock_intent_succeeded.status = 'succeeded'
        mock_intent_succeeded.amount = 10000
        mock_intent_succeeded.charges = Mock()
        mock_intent_succeeded.charges.data = [Mock()]
        mock_intent_succeeded.charges.data[0].id = 'ch_test_complete'
        mock_retrieve.return_value = mock_intent_succeeded
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
        
        # Step 1: Create payment intent
        response = self.client.post('/payment/create-intent',
                                  json={'order_id': self.test_order.id})
        
        self.assertEqual(response.status_code, 200)
        create_data = json.loads(response.data)
        self.assertIn('client_secret', create_data)
        
        # Step 2: Confirm payment
        response = self.client.post('/payment/confirm',
                                  json={'payment_intent_id': 'pi_test_complete'})
        
        self.assertEqual(response.status_code, 200)
        confirm_data = json.loads(response.data)
        self.assertEqual(confirm_data['status'], 'success')
        
        # Verify order status
        db.session.refresh(self.test_order)
        self.assertEqual(self.test_order.status, 'paid')
        self.assertEqual(self.test_order.stripe_payment_intent_id, 'pi_test_complete')


# Test runner and utilities
class PaymentTestRunner:
    """Utility class for running payment tests with reporting"""
    
    @staticmethod
    def run_all_tests():
        """Run all payment tests and generate report"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add test classes
        test_classes = [
            TestPaymentIntentCreation,
            TestPaymentConfirmation,
            TestStripeWebhooks,
            TestPaymentEdgeCases,
            TestPaymentIntegration
        ]
        
        for test_class in test_classes:
            tests = loader.loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result
    
    @staticmethod
    def generate_test_report(result):
        """Generate detailed test report"""
        report = {
            'total_tests': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            'details': {
                'failures': [{'test': str(test), 'error': error} for test, error in result.failures],
                'errors': [{'test': str(test), 'error': error} for test, error in result.errors]
            }
        }
        
        return report


if __name__ == '__main__':
    # Run tests when script is executed directly
    runner = PaymentTestRunner()
    result = runner.run_all_tests()
    
    # Print summary
    print("\n" + "="*50)
    print("PAYMENT TESTING SUMMARY")
    print("="*50)
    
    report = runner.generate_test_report(result)
    print(f"Total Tests: {report['total_tests']}")
    print(f"Failures: {report['failures']}")
    print(f"Errors: {report['errors']}")
    print(f"Success Rate: {report['success_rate']:.1f}%")
    
    if report['failures']:
        print("\nFailures:")
        for failure in report['details']['failures']:
            print(f"  - {failure['test']}")
    
    if report['errors']:
        print("\nErrors:")
        for error in report['details']['errors']:
            print(f"  - {error['test']}")
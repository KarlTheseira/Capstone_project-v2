"""Stripe Service Module"""

import stripe
from config import Config

class StripeService:
    """Handles Stripe payment processing"""
    
    def __init__(self):
        if hasattr(Config, 'STRIPE_SECRET_KEY') and Config.STRIPE_SECRET_KEY:
            stripe.api_key = Config.STRIPE_SECRET_KEY
    
    def create_payment_intent(self, amount, currency='usd', metadata=None):
        """Create a Stripe payment intent"""
        try:
            return stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata=metadata or {}
            )
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return None
    
    def get_payment_intent(self, payment_intent_id):
        """Retrieve a payment intent"""
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return None
    
    def create_customer(self, email, name=None):
        """Create a Stripe customer"""
        try:
            return stripe.Customer.create(
                email=email,
                name=name
            )
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return None

# Create a singleton instance
stripe_service = StripeService()

import uuid
from datetime import datetime, timedelta

class DummyPaymentIntent:
    def __init__(self, amount_cents: int, currency: str = 'usd', metadata=None):
        self.id = f'dummy_pi_{uuid.uuid4().hex[:24]}'
        self.amount = amount_cents
        self.currency = currency
        self.client_secret = f'secret_{uuid.uuid4().hex}'
        self.status = 'requires_confirmation'  # mimic stripe initial state
        self.metadata = metadata or {}
        self.created = int(datetime.utcnow().timestamp())
        self.expires_at = self.created + 30 * 60  # 30 minute expiry

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'currency': self.currency,
            'client_secret': self.client_secret,
            'status': self.status,
            'metadata': self.metadata,
            'created': self.created,
            'expires_at': self.expires_at,
            'object': 'payment_intent'
        }

class DummyPaymentProvider:
    """Lightweight in-memory payment intent simulator.
    NOT for production use. Mirrors minimal subset of Stripe's PaymentIntent.
    """
    def __init__(self):
        self._intents = {}

    def create_payment_intent(self, amount_cents: int, currency: str = 'usd', metadata=None):
        intent = DummyPaymentIntent(amount_cents, currency, metadata)
        self._intents[intent.id] = intent
        return intent

    def retrieve(self, intent_id: str):
        return self._intents.get(intent_id)

    def confirm(self, intent_id: str):
        intent = self._intents.get(intent_id)
        if not intent:
            return None
        if intent.status not in ('requires_confirmation', 'requires_action'):
            return intent
        intent.status = 'succeeded'
        return intent

# Singleton instance
provider = DummyPaymentProvider()

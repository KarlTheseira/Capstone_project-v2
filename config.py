import os

class Config:
    """Flask application configuration"""
    
    # Flask core settings
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///filmcompany.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Admin credentials
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
    
    # Storage backend: local only
    STORAGE_BACKEND = "local"

    # Payments configuration
    PAYMENTS_PROVIDER = os.getenv("PAYMENTS_PROVIDER", "stripe")  # 'dummy' or 'stripe'
    
    # Stripe Configuration (Test Mode)
    STRIPE_PUBLISHABLE_KEY = os.getenv(
        "STRIPE_PUBLISHABLE_KEY", 
        "pk_test_51234567890abcdefghijklmnopqrstuvwxyz1234567890"  # Fake test key
    )
    STRIPE_SECRET_KEY = os.getenv(
        "STRIPE_SECRET_KEY", 
        "sk_test_51234567890abcdefghijklmnopqrstuvwxyz1234567890"  # Fake test key
    )
    
    # Stripe Webhook Configuration
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # Payment Settings
    CURRENCY = os.getenv("CURRENCY", "sgd")
    PAYMENT_SUCCESS_URL = os.getenv("PAYMENT_SUCCESS_URL", "http://127.0.0.1:5001/payment/success")
    PAYMENT_CANCEL_URL = os.getenv("PAYMENT_CANCEL_URL", "http://127.0.0.1:5001/payment/cancel")
    
    # Email Service Configuration
    EMAIL_FUNCTION_URL = os.getenv(
        "EMAIL_FUNCTION_URL", 
        "https://flashstudio-functions.azurewebsites.net/api/EmailNotifications"
    )

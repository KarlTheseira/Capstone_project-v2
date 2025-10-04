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
    
    # Stripe configuration
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # Payment configuration
    CURRENCY = os.getenv("CURRENCY", "sgd")  # Singapore Dollar
    PAYMENT_SUCCESS_URL = os.getenv("PAYMENT_SUCCESS_URL", "/payment-success")
    PAYMENT_CANCEL_URL = os.getenv("PAYMENT_CANCEL_URL", "/cart")
    
    # Google Drive Storage configuration
    GOOGLE_DRIVE_CREDENTIALS_JSON = os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON", "")
    GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

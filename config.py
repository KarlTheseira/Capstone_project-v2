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
    PAYMENTS_PROVIDER = os.getenv("PAYMENTS_PROVIDER", "dummy")  # 'dummy' or 'stripe'
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")  # used when real stripe enabled

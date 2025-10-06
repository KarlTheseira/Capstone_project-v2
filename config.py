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
    
    # Google Drive configuration
    GOOGLE_DRIVE_CREDENTIALS_JSON = os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON")
    GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    # Payments configuration
    PAYMENTS_PROVIDER = os.getenv("PAYMENTS_PROVIDER", "dummy")  # 'dummy' or 'stripe'
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")  # used when real stripe enabled

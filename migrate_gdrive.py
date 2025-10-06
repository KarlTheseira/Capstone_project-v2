#!/usr/bin/env python3
"""
Database migration script for Google Drive integration
Run this to add Google Drive fields to the Product model
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, Product
from config import Config

def migrate_database():
    """Add Google Drive fields to existing Product table"""
    
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('product')]
            
            # Add Google Drive fields if they don't exist
            if 'google_drive_video_id' not in columns:
                print("Adding google_drive_video_id column...")
                db.engine.execute('ALTER TABLE product ADD COLUMN google_drive_video_id VARCHAR(512)')
            
            if 'google_drive_video_url' not in columns:
                print("Adding google_drive_video_url column...")
                db.engine.execute('ALTER TABLE product ADD COLUMN google_drive_video_url VARCHAR(1024)')
                
            if 'video_hosting_type' not in columns:
                print("Adding video_hosting_type column...")
                db.engine.execute("ALTER TABLE product ADD COLUMN video_hosting_type VARCHAR(32) DEFAULT 'local'")
            
            print("Migration completed successfully!")
            print("\nNext steps:")
            print("1. Set up Google Cloud Project and enable Drive API")
            print("2. Create service account and download JSON key")
            print("3. Set environment variables:")
            print("   - GOOGLE_DRIVE_CREDENTIALS_JSON='{your-json-content}'")
            print("   - GOOGLE_DRIVE_FOLDER_ID='your-folder-id'")
            print("4. Restart your application")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            print("\nIf you're using SQLite, the ALTER TABLE command might not work.")
            print("You may need to recreate the database or use Flask-Migrate:")
            print("flask db init")
            print("flask db migrate -m 'Add Google Drive fields'")
            print("flask db upgrade")

if __name__ == '__main__':
    migrate_database()
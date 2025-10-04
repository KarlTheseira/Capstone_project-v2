#!/usr/bin/env python3
"""
Database migration script to add Stripe payment fields to Order model
Run this after updating the models to add the new payment fields
"""
from app import app
from models import db
from sqlalchemy import text

def upgrade_orders_table():
    """Add new payment fields to orders table"""
    
    # Check if columns already exist to avoid errors
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('order')]
        
        migrations = []
        
        # Add payment_method column
        if 'payment_method' not in existing_columns:
            migrations.append('ALTER TABLE "order" ADD COLUMN payment_method VARCHAR(32) DEFAULT \'stripe\'')
        
        # Add payment_completed_at column
        if 'payment_completed_at' not in existing_columns:
            migrations.append('ALTER TABLE "order" ADD COLUMN payment_completed_at DATETIME')
        
        # Update currency default from 'usd' to 'sgd'
        if 'currency' in existing_columns:
            migrations.append('UPDATE "order" SET currency = \'sgd\' WHERE currency = \'usd\' OR currency IS NULL')
        
        # Execute migrations
        if migrations:
            print(f"Executing {len(migrations)} database migrations...")
            for migration in migrations:
                try:
                    db.session.execute(text(migration))
                    print(f"✓ Executed: {migration}")
                except Exception as e:
                    print(f"✗ Failed: {migration} - Error: {e}")
                    db.session.rollback()
                    raise
            
            db.session.commit()
            print("✓ All migrations completed successfully!")
        else:
            print("✓ No migrations needed - database is up to date")

if __name__ == "__main__":
    try:
        upgrade_orders_table()
    except Exception as e:
        print(f"Migration failed: {e}")
        exit(1)
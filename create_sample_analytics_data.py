#!/usr/bin/env python3
"""
Sample data generator for analytics dashboard
Run this script to populate your database with sample data for testing analytics
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, QuoteRequest, Booking, Order, ServicePackage, Product, CORPORATE_CATEGORIES
from datetime import datetime, date, timedelta
import random

def create_sample_data():
    """Create sample data for analytics testing"""
    with app.app_context():
        # Create sample quote requests
        sample_quotes = []
        statuses = ['pending', 'responded', 'quoted', 'closed']
        
        for i in range(50):
            created_date = datetime.now() - timedelta(days=random.randint(1, 90))
            quote = QuoteRequest(
                name=f"Client {i+1}",
                email=f"client{i+1}@example.com",
                phone=f"555-{1000+i}",
                company=f"Company {i+1}" if i % 3 == 0 else None,
                service_type=random.choice(CORPORATE_CATEGORIES),
                event_date=date.today() + timedelta(days=random.randint(7, 180)),
                event_location=f"Location {i+1}",
                budget_range=random.choice(['$1,000-$2,500', '$2,500-$5,000', '$5,000-$10,000', '$10,000+']),
                project_description=f"Sample project description for quote {i+1}",
                status=random.choice(statuses),
                quote_amount=random.randint(150000, 1500000) if random.random() > 0.3 else None,  # 70% chance of quote
                created_at=created_date
            )
            sample_quotes.append(quote)
        
        db.session.add_all(sample_quotes)
        
        # Create sample bookings
        sample_bookings = []
        booking_statuses = ['pending', 'confirmed', 'cancelled', 'completed']
        
        for i in range(30):
            created_date = datetime.now() - timedelta(days=random.randint(1, 60))
            booking_date = date.today() + timedelta(days=random.randint(-30, 60))
            
            booking = Booking(
                name=f"Booking Client {i+1}",
                email=f"booking{i+1}@example.com",
                phone=f"555-{2000+i}",
                service_type=random.choice(CORPORATE_CATEGORIES),
                booking_date=booking_date,
                start_time=datetime.strptime(f"{random.randint(9, 16)}:00", "%H:%M").time(),
                duration_hours=random.choice([1, 2, 3, 4, 6, 8]),
                location=f"Booking Location {i+1}",
                notes=f"Sample booking notes {i+1}",
                status=random.choice(booking_statuses),
                created_at=created_date
            )
            sample_bookings.append(booking)
        
        db.session.add_all(sample_bookings)
        
        # Create sample orders (for revenue data)
        sample_orders = []
        for i in range(25):
            created_date = datetime.now() - timedelta(days=random.randint(1, 180))
            order = Order(
                email=f"customer{i+1}@example.com",
                amount_cents=random.randint(50000, 300000),  # $500 - $3000
                currency="usd",
                status=random.choice(['paid', 'created', 'failed']),
                created_at=created_date
            )
            sample_orders.append(order)
        
        db.session.add_all(sample_orders)
        
        # Create sample service packages
        packages = [
            ServicePackage(
                name="Basic Wedding Package",
                service_type="Wedding Videography",
                description="Perfect for intimate weddings",
                price_cents=150000,  # $1,500
                features='["4 hours coverage", "Highlight reel", "Raw footage"]',
                max_hours=4,
                deliverables="Highlight video + raw files",
                turnaround_days=14,
                popular=False
            ),
            ServicePackage(
                name="Premium Corporate Package",
                service_type="Commercial Production",
                description="Complete corporate video solution",
                price_cents=500000,  # $5,000
                features='["Full day coverage", "Professional editing", "Multiple formats", "Revisions included"]',
                max_hours=8,
                deliverables="Final video in multiple formats",
                turnaround_days=21,
                popular=True
            ),
            ServicePackage(
                name="Event Photography Pro",
                service_type="Event Photography",
                description="Professional event photography",
                price_cents=80000,  # $800
                features='["6 hours coverage", "200+ edited photos", "Online gallery"]',
                max_hours=6,
                deliverables="Online gallery with download rights",
                turnaround_days=7,
                popular=False
            )
        ]
        
        db.session.add_all(packages)
        
        # Commit all sample data
        db.session.commit()
        print("✅ Sample data created successfully!")
        print(f"Created {len(sample_quotes)} quote requests")
        print(f"Created {len(sample_bookings)} bookings")
        print(f"Created {len(sample_orders)} orders")
        print(f"Created {len(packages)} service packages")

if __name__ == "__main__":
    print("🚀 Creating sample data for analytics dashboard...")
    create_sample_data()
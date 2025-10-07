"""Add reviews table and related functionality

This migration script safely adds the Review model table to the existing database.
It includes proper constraints, indexes, and handles existing data gracefully.
"""

import os
import sqlite3
from datetime import datetime

def run_migration(database_path='instance/filmcompany.db'):
    """
    Add the reviews table to the database with proper constraints and indexes
    """
    
    print(f"🔄 Starting Reviews migration on {database_path}")
    
    # Check if database exists
    if not os.path.exists(database_path):
        print(f"❌ Database not found at {database_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Check if reviews table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='reviews'
        """)
        
        if cursor.fetchone():
            print("⚠️  Reviews table already exists. Migration not needed.")
            conn.close()
            return True
        
        print("📝 Creating reviews table...")
        
        # Create the reviews table with all necessary fields
        cursor.execute("""
            CREATE TABLE reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_id INTEGER NULL,
                reviewer_name VARCHAR(100) NOT NULL,
                reviewer_email VARCHAR(120) NULL,
                title VARCHAR(200) NULL,
                comment TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                approved BOOLEAN NOT NULL DEFAULT 0,
                verified_purchase BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """)
        
        print("📊 Adding database indexes for performance...")
        
        # Add indexes for common queries
        cursor.execute("CREATE INDEX idx_reviews_product_id ON reviews (product_id)")
        cursor.execute("CREATE INDEX idx_reviews_approved ON reviews (approved)")
        cursor.execute("CREATE INDEX idx_reviews_rating ON reviews (rating)")
        cursor.execute("CREATE INDEX idx_reviews_created_at ON reviews (created_at)")
        cursor.execute("CREATE INDEX idx_reviews_user_id ON reviews (user_id)")
        
        print("✅ Reviews table created successfully!")
        
        # Check existing tables for verification
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = cursor.fetchall()
        print(f"📋 Current database tables: {', '.join([table[0] for table in tables])}")
        
        # Verify the reviews table structure
        cursor.execute("PRAGMA table_info(reviews)")
        columns = cursor.fetchall()
        print("🔍 Reviews table structure:")
        for column in columns:
            print(f"   - {column[1]} ({column[2]}) {'NOT NULL' if column[3] else 'NULL'}")
        
        # Commit the changes
        conn.commit()
        print("💾 Migration committed successfully!")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

def verify_migration(database_path='instance/filmcompany.db'):
    """
    Verify that the migration was successful
    """
    
    print(f"\n🔍 Verifying migration...")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='reviews'
        """)
        
        if not cursor.fetchone():
            print("❌ Reviews table not found!")
            return False
        
        # Check indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='reviews'
        """)
        indexes = cursor.fetchall()
        expected_indexes = ['idx_reviews_product_id', 'idx_reviews_approved', 'idx_reviews_rating', 'idx_reviews_created_at', 'idx_reviews_user_id']
        
        found_indexes = [idx[0] for idx in indexes if idx[0] in expected_indexes]
        
        print(f"📊 Found indexes: {', '.join(found_indexes) if found_indexes else 'None'}")
        
        # Test basic operations
        cursor.execute("SELECT COUNT(*) FROM reviews")
        count = cursor.fetchone()[0]
        print(f"📋 Current reviews count: {count}")
        
        print("✅ Migration verification successful!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Verification error: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

def add_sample_reviews(database_path='instance/filmcompany.db'):
    """
    Add some sample reviews for testing (optional)
    """
    
    print(f"\n🎬 Adding sample reviews for testing...")
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get some products to review
        cursor.execute("SELECT id, title FROM products LIMIT 3")
        products = cursor.fetchall()
        
        if not products:
            print("⚠️  No products found. Skipping sample reviews.")
            return True
        
        sample_reviews = [
            {
                'product_id': products[0][0],
                'reviewer_name': 'John Smith',
                'reviewer_email': 'john@example.com',
                'title': 'Amazing Quality!',
                'comment': 'The video quality exceeded my expectations. Professional work and quick delivery.',
                'rating': 5,
                'approved': 1,
                'verified_purchase': 1
            },
            {
                'product_id': products[0][0] if len(products) > 0 else 1,
                'reviewer_name': 'Sarah Johnson',
                'reviewer_email': 'sarah@example.com',
                'title': 'Great Service',
                'comment': 'Very happy with the final product. The team was responsive and professional.',
                'rating': 4,
                'approved': 1,
                'verified_purchase': 0
            },
        ]
        
        if len(products) > 1:
            sample_reviews.append({
                'product_id': products[1][0],
                'reviewer_name': 'Mike Davis',
                'reviewer_email': None,
                'title': None,
                'comment': 'Pending review for a recent order. Waiting for approval.',
                'rating': 3,
                'approved': 0,
                'verified_purchase': 1
            })
        
        for review in sample_reviews:
            cursor.execute("""
                INSERT INTO reviews (
                    product_id, reviewer_name, reviewer_email, title, 
                    comment, rating, approved, verified_purchase,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review['product_id'], review['reviewer_name'], review['reviewer_email'],
                review['title'], review['comment'], review['rating'],
                review['approved'], review['verified_purchase'],
                datetime.now(), datetime.now()
            ))
        
        conn.commit()
        print(f"✅ Added {len(sample_reviews)} sample reviews!")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error adding sample reviews: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

def main():
    """
    Main migration function
    """
    
    print("🚀 FlashStudio Reviews Migration")
    print("=" * 50)
    
    database_path = 'instance/filmcompany.db'
    
    # Run the migration
    if run_migration(database_path):
        # Verify it worked
        if verify_migration(database_path):
            
            # Ask if user wants sample data
            response = input("\n💡 Add sample reviews for testing? (y/N): ").lower().strip()
            if response == 'y':
                add_sample_reviews(database_path)
            
            print("\n🎉 Reviews migration completed successfully!")
            print("\nNext steps:")
            print("1. Restart your Flask application")
            print("2. Visit /admin/reviews to manage reviews")
            print("3. Check product pages to see the review sections")
            
        else:
            print("\n❌ Migration verification failed!")
            
    else:
        print("\n❌ Migration failed!")

if __name__ == '__main__':
    main()
from datetime import datetime, timedelta, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, and_, or_
import json

db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price_cents = db.Column(db.Integer, nullable=False)  # store in smallest currency unit
    media_key = db.Column(db.String(512), nullable=False)  # filename or blob name
    mime_type = db.Column(db.String(128))
    thumbnail_key = db.Column(db.String(512))
    video_key = db.Column(db.String(512))  # For video content (local or filename)
    video_thumbnail = db.Column(db.String(512))  # Video preview image
    video_duration = db.Column(db.Integer)  # Duration in seconds
    project_date = db.Column(db.Date)  # When the project was completed
    client_name = db.Column(db.String(255))  # For portfolio pieces
    client_testimonial = db.Column(db.Text)  # Client feedback
    featured = db.Column(db.Boolean, default=False)  # For highlighting top work
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stock = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(128), nullable=True)
    
    # Product customization options (stored as JSON)
    available_sizes = db.Column(db.Text)  # JSON array of available sizes
    available_frames = db.Column(db.Text)  # JSON array of available frames
    
    @property
    def duration_display(self):
        """Format video duration as MM:SS"""
        if not self.video_duration:
            return ""
        minutes = self.video_duration // 60
        seconds = self.video_duration % 60
        return f"{minutes}:{seconds:02d}"
        
    @property
    def is_video(self):
        """Check if this product has video content"""
        return bool(self.video_key)
    
    @property
    def video_stream_url(self):
        """Get the local video streaming URL"""
        if self.video_key:
            # Local video file
            from flask import url_for
            return url_for('public.video', video_id=self.id)
        return None
    
    @property
    def size_options_list(self):
        """Get available sizes as a list"""
        if not self.available_sizes:
            return ["20cm x 30cm", "40cm x 60cm"]  # Default options
        try:
            return json.loads(self.available_sizes)
        except:
            return ["20cm x 30cm", "40cm x 60cm"]  # Fallback to defaults
    
    @size_options_list.setter
    def size_options_list(self, value):
        """Set available sizes from a list"""
        self.available_sizes = json.dumps(value) if value else None
    
    @property
    def frame_options_list(self):
        """Get available frames as a list"""
        if not self.available_frames:
            return ["No frame", "Black", "White"]  # Default options
        try:
            return json.loads(self.available_frames)
        except:
            return ["No frame", "Black", "White"]  # Fallback to defaults
    
    @frame_options_list.setter  
    def frame_options_list(self, value):
        """Set available frames from a list"""
        self.available_frames = json.dumps(value) if value else None
        return bool(self.video_key)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(16), nullable=False, default="usd")
    stripe_payment_intent = db.Column(db.String(255))
    status = db.Column(db.String(32), default="created")  # created, paid, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="orders")
    
    @property
    def total_display(self):
        """Display total amount in currency format"""
        return f"S$ {self.amount_cents / 100.0:.2f}"
    
    @property
    def customer_email(self):
        """Get customer email, prefer user.email if available, fallback to order.email"""
        return self.user.email if self.user else self.email
    
    @property
    def item_count(self):
        """Get total number of items in this order"""
        return sum(item.quantity for item in self.items)
    
    @property
    def has_items(self):
        """Check if order has any items"""
        return len(self.items) > 0

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price_cents = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", backref=db.backref("items", lazy=True))
    product = db.relationship("Product")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)  # optional

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class QuoteRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    company = db.Column(db.String(255))
    service_type = db.Column(db.String(128), nullable=False)
    event_date = db.Column(db.Date)
    event_location = db.Column(db.String(255))
    budget_range = db.Column(db.String(64))
    project_description = db.Column(db.Text)
    additional_services = db.Column(db.String(512))  # JSON string for multiple services
    urgent = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(32), default="pending")  # pending, responded, quoted, closed
    admin_notes = db.Column(db.Text)
    quote_amount = db.Column(db.Integer)  # quote in cents
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def quote_display(self):
        """Format quote amount for display"""
        if self.quote_amount:
            return f"${self.quote_amount / 100:.2f}"
        return "Not quoted"

class ServicePackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)  # Basic, Premium, Enterprise
    service_type = db.Column(db.String(128), nullable=False)  # Wedding, Commercial, etc.
    description = db.Column(db.Text)
    price_cents = db.Column(db.Integer, nullable=False)
    features = db.Column(db.Text)  # JSON string of included features
    max_hours = db.Column(db.Integer)  # Maximum hours included
    deliverables = db.Column(db.Text)  # What client receives
    turnaround_days = db.Column(db.Integer)  # Delivery timeframe
    popular = db.Column(db.Boolean, default=False)  # Mark popular packages
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Corporate service category constants
CORPORATE_CATEGORIES = [
    "Wedding Videography",
    "Commercial Production", 
    "Event Photography",
    "Live Streaming",
    "Documentary Production",
    "Promotional Videos",
    "Drone Footage"
]

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    service_type = db.Column(db.String(128), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time)
    duration_hours = db.Column(db.Integer, default=1)  # Duration in hours
    location = db.Column(db.String(255))
    notes = db.Column(db.Text)
    status = db.Column(db.String(32), default="pending")  # pending, confirmed, cancelled, completed
    quote_request_id = db.Column(db.Integer, db.ForeignKey("quote_request.id"))  # Link to quote if exists
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    quote_request = db.relationship("QuoteRequest", backref="bookings")
    
    @property
    def is_past(self):
        """Check if booking date has passed"""
        today = datetime.now().date()
        return self.booking_date < today
    
    @property 
    def date_display(self):
        """Format booking date for display"""
        return self.booking_date.strftime('%B %d, %Y')
    
    @property
    def time_display(self):
        """Format booking time for display"""
        start = self.start_time.strftime('%I:%M %p')
        if self.end_time:
            end = self.end_time.strftime('%I:%M %p')
            return f"{start} - {end}"
        return start

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    notes = db.Column(db.String(255))  # Reason for unavailability
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Analytics Class
class Analytics:
    """Analytics helper class for dashboard metrics"""
    
    @staticmethod
    def get_dashboard_stats(date_range=30):
        """Get key dashboard statistics"""
        # Ensure date_range is an integer
        try:
            date_range = int(date_range)
        except (ValueError, TypeError):
            date_range = 30
            
        end_date = date.today()
        start_date = end_date - timedelta(days=date_range)
        
        # Revenue stats
        total_revenue = db.session.query(func.sum(Order.amount_cents)).filter(
            Order.status == 'paid'
        ).scalar() or 0
        
        period_revenue = db.session.query(func.sum(Order.amount_cents)).filter(
            and_(Order.status == 'paid', Order.created_at >= start_date)
        ).scalar() or 0
        
        # Quote stats
        total_quotes = QuoteRequest.query.count()
        pending_quotes = QuoteRequest.query.filter(QuoteRequest.status == 'pending').count()
        
        period_quotes = QuoteRequest.query.filter(
            QuoteRequest.created_at >= start_date
        ).count()
        
        # Booking stats
        total_bookings = Booking.query.count()
        confirmed_bookings = Booking.query.filter(Booking.status == 'confirmed').count()
        
        period_bookings = Booking.query.filter(
            Booking.created_at >= start_date
        ).count()
        
        # Conversion rate
        quoted_count = QuoteRequest.query.filter(QuoteRequest.status == 'quoted').count()
        conversion_rate = (quoted_count / total_quotes * 100) if total_quotes > 0 else 0
        
        return {
            'total_revenue': total_revenue / 100,  # Convert to dollars
            'period_revenue': period_revenue / 100,
            'total_quotes': total_quotes,
            'pending_quotes': pending_quotes,
            'period_quotes': period_quotes,
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'period_bookings': period_bookings,
            'conversion_rate': round(conversion_rate, 1),
            'avg_quote_value': Analytics.get_average_quote_value()
        }
    
    @staticmethod
    def get_revenue_trend(months=6):
        """Get monthly revenue trend"""
        # Ensure months is an integer
        try:
            months = int(months)
        except (ValueError, TypeError):
            months = 6
            
        end_date = date.today()
        # Calculate start date properly handling year boundaries
        start_year = end_date.year
        start_month = end_date.month - months + 1
        
        if start_month <= 0:
            start_year -= 1
            start_month += 12
            
        start_date = date(start_year, start_month, 1)
        
        revenue_data = db.session.query(
            func.extract('year', Order.created_at).label('year'),
            func.extract('month', Order.created_at).label('month'),
            func.sum(Order.amount_cents).label('revenue')
        ).filter(
            and_(Order.status == 'paid', Order.created_at >= start_date)
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        return [
            {
                'month': f"{int(row.year)}-{int(row.month):02d}",
                'revenue': (row.revenue or 0) / 100
            } for row in revenue_data
        ]
    
    @staticmethod
    def get_service_popularity():
        """Get most popular services from quotes"""
        service_data = db.session.query(
            QuoteRequest.service_type,
            func.count(QuoteRequest.id).label('count')
        ).group_by(QuoteRequest.service_type).order_by(
            func.count(QuoteRequest.id).desc()
        ).limit(10).all()
        
        return [
            {'service': row.service_type, 'count': row.count}
            for row in service_data
        ]
    
    @staticmethod
    def get_quote_conversion_funnel():
        """Get quote conversion funnel data"""
        total = QuoteRequest.query.count()
        responded = QuoteRequest.query.filter(QuoteRequest.status == 'responded').count()
        quoted = QuoteRequest.query.filter(QuoteRequest.status == 'quoted').count()
        closed = QuoteRequest.query.filter(QuoteRequest.status == 'closed').count()
        
        return {
            'total': total,
            'responded': responded,
            'quoted': quoted,
            'closed': closed
        }
    
    @staticmethod
    def get_booking_analytics():
        """Get booking analytics"""
        today = date.today()
        
        # Upcoming bookings
        upcoming = Booking.query.filter(
            and_(Booking.booking_date >= today, Booking.status == 'confirmed')
        ).count()
        
        # This month's bookings
        month_start = today.replace(day=1)
        this_month = Booking.query.filter(
            and_(Booking.booking_date >= month_start, Booking.booking_date <= today)
        ).count()
        
        # Most popular booking days
        day_popularity = db.session.query(
            func.extract('dow', Booking.booking_date).label('day_of_week'),
            func.count(Booking.id).label('count')
        ).group_by('day_of_week').order_by('count').all()
        
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        day_data = [
            {'day': days[int(row.day_of_week)], 'count': row.count}
            for row in day_popularity
        ]
        
        return {
            'upcoming_bookings': upcoming,
            'month_bookings': this_month,
            'popular_days': day_data
        }
    
    @staticmethod
    def get_average_quote_value():
        """Get average quote value"""
        avg_value = db.session.query(
            func.avg(QuoteRequest.quote_amount)
        ).filter(QuoteRequest.quote_amount.isnot(None)).scalar()
        
        return round((avg_value or 0) / 100, 2)
    
    @staticmethod
    def get_recent_activities(limit=10):
        """Get recent system activities"""
        activities = []
        
        # Recent quotes
        recent_quotes = QuoteRequest.query.order_by(
            QuoteRequest.created_at.desc()
        ).limit(5).all()
        
        for quote in recent_quotes:
            activities.append({
                'type': 'quote',
                'message': f'New quote request from {quote.name} for {quote.service_type}',
                'timestamp': quote.created_at,
                'status': quote.status
            })
        
        # Recent bookings
        recent_bookings = Booking.query.order_by(
            Booking.created_at.desc()
        ).limit(5).all()
        
        for booking in recent_bookings:
            activities.append({
                'type': 'booking',
                'message': f'New booking from {booking.name} for {booking.date_display}',
                'timestamp': booking.created_at,
                'status': booking.status
            })
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:limit]


class Review(db.Model):
    """Customer product reviews"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow anonymous reviews
    reviewer_name = db.Column(db.String(255), nullable=False)  # For anonymous users
    reviewer_email = db.Column(db.String(255), nullable=True)  # Optional contact
    rating = db.Column(db.Integer, nullable=False)  # 1-5 star rating
    title = db.Column(db.String(255), nullable=True)  # Review title/headline
    comment = db.Column(db.Text, nullable=False)  # Review text
    verified_purchase = db.Column(db.Boolean, default=False)  # If user bought the item
    approved = db.Column(db.Boolean, default=True)  # Admin approval (auto-approve for now)
    helpful_count = db.Column(db.Integer, default=0)  # Number of helpful votes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref=db.backref('reviews', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    
    @property
    def display_name(self):
        """Get display name - use User name if logged in, otherwise reviewer_name"""
        if self.user:
            return self.user.email.split('@')[0].title()
        return self.reviewer_name
    
    @property
    def star_display(self):
        """Get HTML star display"""
        full_stars = self.rating
        empty_stars = 5 - self.rating
        return '★' * full_stars + '☆' * empty_stars
    
    @classmethod
    def get_product_stats(cls, product_id):
        """Get review statistics for a product"""
        reviews = cls.query.filter_by(product_id=product_id, approved=True).all()
        if not reviews:
            return {
                'count': 0,
                'average_rating': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        total_rating = sum(r.rating for r in reviews)
        average = round(total_rating / len(reviews), 1)
        
        # Rating distribution
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for review in reviews:
            distribution[review.rating] += 1
            
        return {
            'count': len(reviews),
            'average_rating': average,
            'rating_distribution': distribution,
            'reviews': reviews
        }

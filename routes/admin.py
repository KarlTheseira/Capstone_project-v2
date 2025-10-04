from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify, make_response
from models import Product, Order, QuoteRequest, ServicePackage, Booking, Analytics, db, CORPORATE_CATEGORIES
from utils.media import save_media
from utils.payment_analytics import payment_analytics
from utils.rate_limiting import rate_limit
from config import Config
import json
import csv
from datetime import datetime, date, timedelta
from io import StringIO

# Import size and frame options for product customization
SIZE_OPTIONS = {
    "20cm x 30cm": 0,        # base price
    "40cm x 60cm": 8000,     # +S$ 80.00
}
FRAME_OPTIONS = {
    "No frame": 0,
    "Black": 2000,           # +S$ 20.00
    "White": 2000,           # +S$ 20.00
}

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_admin():
    """Check if user has admin privileges"""
    # Check multiple admin session indicators for robustness
    is_admin = (
        session.get("admin") == True or 
        session.get("admin_logged_in") == True or 
        session.get("user_type") == "admin"
    )
    
    if not is_admin:
        abort(403)

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("admin_login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    # Accept both admin@flashstudios.com and admin as username
    valid_username = (username == Config.ADMIN_USERNAME or username == "admin@flashstudios.com")
    valid_password = (password == Config.ADMIN_PASSWORD)

    if valid_username and valid_password:
        # Clear any existing sessions
        session.clear()
        
        # Set comprehensive admin session
        session.permanent = True
        session["admin"] = True
        session["admin_logged_in"] = True
        session["user_type"] = "admin"
        session.modified = True
        
        return redirect(url_for("admin.dashboard"))

    return render_template("admin_login.html", error="Invalid credentials")

@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    session.pop("admin", None)
    return redirect(url_for("admin.login"))

@admin_bp.route('/analytics')
def analytics():
    """Payment analytics dashboard"""
    require_admin()
    
    # Get time period from request (default 30 days)
    days = request.args.get('days', 30, type=int)
    if days not in [7, 30, 90, 365]:
        days = 30
    
    # Get comprehensive analytics data
    analytics_data = payment_analytics.get_comprehensive_dashboard(days)
    
    return render_template('admin_analytics.html', 
                         analytics=analytics_data, 
                         selected_days=days)

@admin_bp.route('/analytics/api')
@rate_limit('analytics')
def analytics_api():
    """API endpoint for analytics data (AJAX)"""
    require_admin()
    
    days = request.args.get('days', 30, type=int)
    metric = request.args.get('metric', 'comprehensive')
    
    if metric == 'revenue':
        data = payment_analytics.get_revenue_summary(days)
    elif metric == 'success_rate':
        data = payment_analytics.get_payment_success_rate(days)
    elif metric == 'chart_data':
        data = payment_analytics.get_daily_revenue_chart(days)
    elif metric == 'products':
        data = payment_analytics.get_top_products(days)
    elif metric == 'customers':
        data = payment_analytics.get_customer_metrics(days)
    else:
        data = payment_analytics.get_comprehensive_dashboard(days)
    
    return jsonify(data)

@admin_bp.route('/rate-limits')
def rate_limits():
    """Rate limiting monitoring dashboard"""
    require_admin()
    
    from utils.rate_limiting import rate_limit_monitor
    
    # Get rate limit statistics
    stats = rate_limit_monitor.get_rate_limit_stats(24)
    health = rate_limit_monitor.check_system_health()
    
    return render_template('admin_rate_limits.html', 
                         stats=stats, 
                         health=health)

@admin_bp.route('/rate-limits/api')
def rate_limits_api():
    """API endpoint for rate limit monitoring data"""
    require_admin()
    
    from utils.rate_limiting import rate_limit_monitor
    
    hours = request.args.get('hours', 24, type=int)
    
    data = {
        'stats': rate_limit_monitor.get_rate_limit_stats(hours),
        'health': rate_limit_monitor.check_system_health()
    }
    
    return jsonify(data)

@admin_bp.route("/", methods=["GET", "POST"])
def dashboard():
    require_admin()

    if request.method == "POST":
        title       = request.form.get("title")
        description = request.form.get("description")
        price_cents = int(float(request.form.get("price", 0)) * 100)
        file        = request.files.get("media")
        thumb       = request.files.get("thumbnail")
        stock       = int(request.form.get("stock", 0))

        if not title or not file:
            return render_template(
                "admin_dashboard.html",
                error="Title and media file are required.",
                products=Product.query.order_by(Product.created_at.desc()).all()
            )

        media_key, _url = save_media(file)
        thumbnail_key = None
        if thumb:
            thumbnail_key, _ = save_media(thumb)

        category = request.form.get("category", "").strip()
        
        product = Product(
            title=title,
            description=description,
            price_cents=price_cents,
            media_key=media_key,
            mime_type=file.mimetype,
            thumbnail_key=thumbnail_key,
            stock=stock,
            category=category
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully.", "success")
        return redirect(url_for("admin.dashboard"))

    # Get analytics data
    date_range = request.args.get('range', '30', type=int)
    analytics_data = Analytics.get_dashboard_stats(date_range)
    revenue_trend = Analytics.get_revenue_trend(6)
    service_popularity = Analytics.get_service_popularity()
    conversion_funnel = Analytics.get_quote_conversion_funnel()
    booking_analytics = Analytics.get_booking_analytics()
    recent_activities = Analytics.get_recent_activities(10)

    products = Product.query.order_by(Product.created_at.desc()).all()
    
    return render_template(
        "admin_dashboard.html", 
        products=products, 
        categories=CORPORATE_CATEGORIES,
        analytics=analytics_data,
        revenue_trend=revenue_trend,
        service_popularity=service_popularity,
        conversion_funnel=conversion_funnel,
        booking_analytics=booking_analytics,
        recent_activities=recent_activities,
        selected_range=date_range
    )

@admin_bp.route("/update_stock/<int:product_id>", methods=["POST"])
def update_stock(product_id):
    require_admin()
    product = Product.query.get_or_404(product_id)
    new_stock = request.form.get("stock")

    try:
        product.stock = int(new_stock)
        db.session.commit()
        flash("Stock updated successfully.", "success")
    except (ValueError, TypeError):
        flash("Invalid stock value.", "danger")

    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/delete/<int:product_id>", methods=["POST"])
def delete(product_id):
    require_admin()
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully.", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    require_admin()
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        # basic fields
        product.title = request.form.get("title", "").strip()
        product.description = request.form.get("description", "").strip()
        product.stock = request.form.get("stock", type=int) or 0

        # price -> cents
        price = request.form.get("price", type=float)
        if price is not None:
            product.price_cents = int(round(price * 100))

        # optional category
        category = request.form.get("category", "").strip()
        if category:
            product.category = category

        # Handle customization options
        available_sizes = request.form.getlist("available_sizes")
        available_frames = request.form.getlist("available_frames")
        
        if available_sizes:
            product.size_options_list = available_sizes
        if available_frames:
            product.frame_options_list = available_frames

        # optional file updates
        file = request.files.get("media")
        thumb = request.files.get("thumbnail")

        if file and file.filename:
            media_key, _url = save_media(file)
            product.media_key = media_key
            product.mime_type = file.mimetype

        if thumb and thumb.filename:
            thumbnail_key, _ = save_media(thumb)
            product.thumbnail_key = thumbnail_key

        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin.dashboard"))

    # GET -> render edit form with corporate categories
    return render_template("admin_product_edit.html", 
                         product=product, 
                         categories=CORPORATE_CATEGORIES,
                         size_options=SIZE_OPTIONS,
                         frame_options=FRAME_OPTIONS)

@admin_bp.route('/analytics')
def admin_analytics():
    """Payment analytics dashboard"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    
    # Get time period from request (default 30 days)
    days = request.args.get('days', 30, type=int)
    if days not in [7, 30, 90, 365]:
        days = 30
    
    # Get comprehensive analytics data
    analytics_data = payment_analytics.get_comprehensive_dashboard(days)
    
    return render_template('admin_analytics.html', 
                         analytics=analytics_data, 
                         selected_days=days)

@admin_bp.route('/analytics/api')
def admin_analytics_api():
    """API endpoint for analytics data (AJAX)"""
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    days = request.args.get('days', 30, type=int)
    metric = request.args.get('metric', 'comprehensive')
    
    if metric == 'revenue':
        data = payment_analytics.get_revenue_summary(days)
    elif metric == 'success_rate':
        data = payment_analytics.get_payment_success_rate(days)
    elif metric == 'chart_data':
        data = payment_analytics.get_daily_revenue_chart(days)
    elif metric == 'products':
        data = payment_analytics.get_top_products(days)
    elif metric == 'customers':
        data = payment_analytics.get_customer_metrics(days)
    else:
        data = payment_analytics.get_comprehensive_dashboard(days)
    
    return jsonify(data)

@admin_bp.route('/orders')
def admin_orders():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
def order_detail(order_id):
    require_admin()
    order = Order.query.get_or_404(order_id)

    if request.method == "POST":
        new_status = request.form.get("status")
        if new_status:
            order.status = new_status
            db.session.commit()
            flash("Order status updated.", "success")
        return redirect(url_for("admin.orders"))

    return render_template("admin_order_detail.html", order=order)

@admin_bp.route("/quotes")
def quotes():
    require_admin()
    quotes = QuoteRequest.query.order_by(QuoteRequest.created_at.desc()).all()
    return render_template("admin_quotes.html", quotes=quotes)

@admin_bp.route("/quotes/<int:quote_id>", methods=["GET", "POST"])
def quote_detail(quote_id):
    require_admin()
    quote = QuoteRequest.query.get_or_404(quote_id)
    
    if request.method == "POST":
        quote.status = request.form.get("status", quote.status)
        quote.admin_notes = request.form.get("admin_notes", "")
        
        # Handle quote amount
        quote_amount = request.form.get("quote_amount")
        if quote_amount:
            try:
                quote.quote_amount = int(float(quote_amount) * 100)  # Convert to cents
            except (ValueError, TypeError):
                flash("Invalid quote amount.", "danger")
                return redirect(url_for("admin.quote_detail", quote_id=quote_id))
        
        db.session.commit()
        flash("Quote updated successfully.", "success")
        return redirect(url_for("admin.quotes"))
    
    return render_template("admin_quote_detail.html", quote=quote)

@admin_bp.route("/service-packages", methods=["GET", "POST"])
def service_packages():
    require_admin()
    
    if request.method == "POST":
        # Create new service package
        name = request.form.get("name")
        service_type = request.form.get("service_type")
        description = request.form.get("description")
        price = request.form.get("price")
        features = request.form.getlist("features")
        max_hours = request.form.get("max_hours", type=int)
        deliverables = request.form.get("deliverables")
        turnaround_days = request.form.get("turnaround_days", type=int)
        popular = "popular" in request.form
        
        if not name or not service_type or not price:
            flash("Name, service type, and price are required.", "danger")
        else:
            try:
                price_cents = int(float(price) * 100)
                package = ServicePackage(
                    name=name,
                    service_type=service_type,
                    description=description,
                    price_cents=price_cents,
                    features=json.dumps(features),
                    max_hours=max_hours,
                    deliverables=deliverables,
                    turnaround_days=turnaround_days,
                    popular=popular
                )
                db.session.add(package)
                db.session.commit()
                flash("Service package created successfully.", "success")
            except (ValueError, TypeError):
                flash("Invalid price format.", "danger")
        
        return redirect(url_for("admin.service_packages"))
    
    packages = ServicePackage.query.order_by(ServicePackage.service_type, ServicePackage.name).all()
    return render_template("admin_service_packages.html", packages=packages, categories=CORPORATE_CATEGORIES)

@admin_bp.route("/service-packages/<int:package_id>/delete", methods=["POST"])
def delete_package(package_id):
    require_admin()
    package = ServicePackage.query.get_or_404(package_id)
    db.session.delete(package)
    db.session.commit()
    flash("Service package deleted successfully.", "success")
    return redirect(url_for("admin.service_packages"))

@admin_bp.route("/bookings")
def bookings():
    require_admin()
    today = date.today()
    upcoming_bookings = Booking.query.filter(
        Booking.booking_date >= today
    ).order_by(Booking.booking_date, Booking.start_time).all()
    
    past_bookings = Booking.query.filter(
        Booking.booking_date < today
    ).order_by(Booking.booking_date.desc()).limit(50).all()
    
    return render_template("admin_bookings.html", 
                         upcoming_bookings=upcoming_bookings, 
                         past_bookings=past_bookings)

@admin_bp.route("/bookings/<int:booking_id>", methods=["GET", "POST"])
def booking_detail(booking_id):
    require_admin()
    booking = Booking.query.get_or_404(booking_id)
    
    if request.method == "POST":
        booking.status = request.form.get("status", booking.status)
        booking.notes = request.form.get("admin_notes", booking.notes)
        
        db.session.commit()
        flash("Booking updated successfully.", "success")
        return redirect(url_for("admin.bookings"))
    
    return render_template("admin_booking_detail.html", booking=booking)

@admin_bp.route("/bookings/<int:booking_id>/delete", methods=["POST"])
def delete_booking(booking_id):
    require_admin()
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    flash("Booking deleted successfully.", "success")
    return redirect(url_for("admin.bookings"))

# Analytics Routes (Legacy - keeping for compatibility)
@admin_bp.route("/api/analytics/<metric>")
def legacy_analytics_api(metric):
    """Legacy API endpoint for real-time analytics data"""
    require_admin()
    
    date_range = request.args.get('range', '30')
    try:
        date_range = int(date_range)
    except (ValueError, TypeError):
        date_range = 30
    
    if metric == 'dashboard':
        data = Analytics.get_dashboard_stats(date_range)
    elif metric == 'revenue-trend':
        data = Analytics.get_revenue_trend(6)
    elif metric == 'service-popularity':
        data = Analytics.get_service_popularity()
    elif metric == 'conversion-funnel':
        data = Analytics.get_quote_conversion_funnel()
    elif metric == 'booking-analytics':
        data = Analytics.get_booking_analytics()
    elif metric == 'recent-activities':
        data = Analytics.get_recent_activities(10)
    else:
        return jsonify({'error': 'Invalid metric'}), 400
    
    return jsonify(data)

@admin_bp.route("/analytics/export")
def export_analytics():
    """Export analytics data as CSV"""
    require_admin()
    
    export_type = request.args.get('type', 'dashboard')
    date_range = request.args.get('range', '30', type=int)
    
    if export_type == 'dashboard':
        data = Analytics.get_dashboard_stats(date_range)
        fieldnames = ['metric', 'value']
        rows = [
            {'metric': 'Total Revenue', 'value': f"${data['total_revenue']:.2f}"},
            {'metric': 'Period Revenue', 'value': f"${data['period_revenue']:.2f}"},
            {'metric': 'Total Quotes', 'value': data['total_quotes']},
            {'metric': 'Pending Quotes', 'value': data['pending_quotes']},
            {'metric': 'Total Bookings', 'value': data['total_bookings']},
            {'metric': 'Confirmed Bookings', 'value': data['confirmed_bookings']},
            {'metric': 'Conversion Rate', 'value': f"{data['conversion_rate']}%"},
            {'metric': 'Average Quote Value', 'value': f"${data['avg_quote_value']:.2f}"},
        ]
    elif export_type == 'quotes':
        quotes = QuoteRequest.query.all()
        fieldnames = ['name', 'email', 'service_type', 'status', 'quote_amount', 'created_at']
        rows = [
            {
                'name': q.name,
                'email': q.email,
                'service_type': q.service_type,
                'status': q.status,
                'quote_amount': q.quote_display if q.quote_amount else 'Not quoted',
                'created_at': q.created_at.strftime('%Y-%m-%d %H:%M')
            } for q in quotes
        ]
    elif export_type == 'bookings':
        bookings = Booking.query.all()
        fieldnames = ['name', 'email', 'service_type', 'booking_date', 'start_time', 'status', 'created_at']
        rows = [
            {
                'name': b.name,
                'email': b.email,
                'service_type': b.service_type,
                'booking_date': b.booking_date.strftime('%Y-%m-%d'),
                'start_time': b.start_time.strftime('%H:%M'),
                'status': b.status,
                'created_at': b.created_at.strftime('%Y-%m-%d %H:%M')
            } for b in bookings
        ]
    else:
        flash("Invalid export type.", "error")
        return redirect(url_for("admin.dashboard"))
    
    # Create CSV
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    
    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={export_type}_export_{date.today().strftime('%Y%m%d')}.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response

@admin_bp.route("/customization-options", methods=["GET", "POST"])
def customization_options():
    """Manage global size and frame options"""
    require_admin()
    
    if request.method == "POST":
        # Handle form submission to update global options
        action = request.form.get("action")
        
        if action == "add_size":
            size_name = request.form.get("size_name", "").strip()
            size_price = request.form.get("size_price", type=float, default=0)
            if size_name:
                SIZE_OPTIONS[size_name] = int(size_price * 100)  # Convert to cents
                flash(f"Added size option: {size_name}", "success")
        
        elif action == "add_frame":
            frame_name = request.form.get("frame_name", "").strip()  
            frame_price = request.form.get("frame_price", type=float, default=0)
            if frame_name:
                FRAME_OPTIONS[frame_name] = int(frame_price * 100)  # Convert to cents
                flash(f"Added frame option: {frame_name}", "success")
        
        elif action == "delete_size":
            size_to_delete = request.form.get("size_to_delete")
            if size_to_delete and size_to_delete in SIZE_OPTIONS:
                del SIZE_OPTIONS[size_to_delete]
                flash(f"Deleted size option: {size_to_delete}", "success")
        
        elif action == "delete_frame":
            frame_to_delete = request.form.get("frame_to_delete")
            if frame_to_delete and frame_to_delete in FRAME_OPTIONS:
                del FRAME_OPTIONS[frame_to_delete]
                flash(f"Deleted frame option: {frame_to_delete}", "success")
        
        return redirect(url_for("admin.customization_options"))
    
    return render_template("admin_customization_options.html", 
                         size_options=SIZE_OPTIONS,
                         frame_options=FRAME_OPTIONS)

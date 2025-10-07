from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify
from models import Product, User, Order, OrderItem, QuoteRequest, ServicePackage, Booking, Availability, db, CORPORATE_CATEGORIES
from datetime import datetime, date, timedelta, time
import uuid
import json

public_bp = Blueprint("public", __name__)

# -----------------------------
# Pricing options (cents)
# -----------------------------
SIZE_OPTIONS = {
    "20cm x 30cm": 0,        # base price
    "40cm x 60cm": 8000,     # +S$ 80.00
}
FRAME_OPTIONS = {
    "No frame": 0,
    "Black": 2000,           # +S$ 20.00
    "White": 2000,           # +S$ 20.00
}

# -----------------------------
# Helpers: cart & pricing
# -----------------------------
def _get_cart():
    """Return cart list from session, create if missing."""
    return session.setdefault("cart", [])

def _save_cart(cart):
    session["cart"] = cart
    session.modified = True

def _unit_price_cents(product, size, frame):
    return int(product.price_cents) + int(SIZE_OPTIONS.get(size, 0)) + int(FRAME_OPTIONS.get(frame, 0))

def _cart_totals():
    cart = _get_cart()
    total = sum(int(item["unit_price_cents"]) * int(item["qty"]) for item in cart)
    return total

# -----------------------------
# Public pages
# -----------------------------
@public_bp.route("/corporate-services")
def corporate_services():
    """Corporate services landing page with detailed service offerings."""
    services = [
        {
            "name": "Wedding Videography",
            "description": "Capture your special day with cinematic wedding videos that tell your unique love story.",
            "features": ["Multi-camera setup", "Drone footage", "Same-day highlights", "Full ceremony recording"],
            "price_range": "From $1,200",
            "image": "wedding_video.jpg"
        },
        {
            "name": "Commercial Production",
            "description": "Professional commercial videos that showcase your brand and drive business growth.",
            "features": ["Script development", "Professional lighting", "Brand storytelling", "Multi-format delivery"],
            "price_range": "From $2,500",
            "image": "commercial_video.jpg"
        },
        {
            "name": "Event Photography",
            "description": "Comprehensive event coverage with high-quality photos that capture every important moment.",
            "features": ["Full event coverage", "Professional editing", "Online gallery", "Print packages"],
            "price_range": "From $800",
            "image": "event_photo.jpg"
        },
        {
            "name": "Live Streaming",
            "description": "Professional live streaming services for events, conferences, and special occasions.",
            "features": ["HD streaming", "Multi-platform broadcast", "Real-time monitoring", "Recording included"],
            "price_range": "From $500",
            "image": "live_stream.jpg"
        },
        {
            "name": "Documentary Production",
            "description": "Tell compelling stories through professional documentary filmmaking.",
            "features": ["Story development", "Interview setup", "Location scouting", "Post-production"],
            "price_range": "From $3,000",
            "image": "documentary.jpg"
        },
        {
            "name": "Promotional Videos",
            "description": "Engaging promotional content that highlights your products and services.",
            "features": ["Concept development", "Professional filming", "Motion graphics", "Social media formats"],
            "price_range": "From $1,500",
            "image": "promo_video.jpg"
        },
        {
            "name": "Drone Footage",
            "description": "Stunning aerial photography and videography for unique perspectives.",
            "features": ["4K aerial footage", "Licensed drone pilot", "Weather monitoring", "Insurance coverage"],
            "price_range": "From $400",
            "image": "drone_footage.jpg"
        }
    ]
    
    return render_template("corporate_services.html", services=services)

@public_bp.route("/request-quote", methods=["GET", "POST"])
def request_quote():
    """Quote request form for corporate services."""
    if request.method == "POST":
        # Get form data
        quote_request = QuoteRequest(
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            company=request.form.get("company", "").strip(),
            service_type=request.form.get("service_type", ""),
            project_description=request.form.get("project_description", "").strip(),
            budget_range=request.form.get("budget_range", ""),
            additional_services=request.form.get("additional_services", "").strip(),
            urgent="urgent" in request.form
        )
        
        # Handle event date
        event_date = request.form.get("event_date")
        if event_date:
            try:
                quote_request.event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        quote_request.event_location = request.form.get("event_location", "").strip()
        
        # Validate required fields
        if not quote_request.name or not quote_request.email or not quote_request.service_type:
            flash("Please fill in all required fields (Name, Email, Service Type).", "danger")
            return render_template("request_quote.html", 
                                 form_data=request.form, 
                                 categories=CORPORATE_CATEGORIES)
        
        # Save quote request
        try:
            db.session.add(quote_request)
            db.session.commit()
            flash("Your quote request has been submitted successfully! We'll get back to you within 24 hours.", "success")
            return redirect(url_for("public.request_quote"))
        except Exception as e:
            db.session.rollback()
            flash("There was an error submitting your request. Please try again.", "danger")
    
    # Pre-fill service type from URL parameter
    selected_service = request.args.get("service", "")
    
    return render_template("request_quote.html", 
                         categories=CORPORATE_CATEGORIES, 
                         selected_service=selected_service)

@public_bp.route("/portfolio")
def portfolio():
    """Portfolio page showcasing corporate work."""
    # Get portfolio items by category
    portfolio_items = {}
    for category in CORPORATE_CATEGORIES:
        items = Product.query.filter_by(category=category).filter(Product.featured == True).all()
        if items:
            portfolio_items[category] = items
    
    return render_template("portfolio.html", portfolio_items=portfolio_items, categories=CORPORATE_CATEGORIES)

@public_bp.route("/service-packages")
def service_packages():
    """Display service packages to customers."""
    # Group packages by service type
    packages_by_service = {}
    packages = ServicePackage.query.filter_by(active=True).order_by(ServicePackage.service_type, ServicePackage.price_cents).all()
    
    for package in packages:
        if package.service_type not in packages_by_service:
            packages_by_service[package.service_type] = []
        packages_by_service[package.service_type].append(package)
    
    return render_template("service_packages.html", packages_by_service=packages_by_service)

@public_bp.route("/service-packages/<int:package_id>")
def package_detail(package_id):
    """View detailed information about a specific package."""
    package = ServicePackage.query.get_or_404(package_id)
    
    # Parse features if they're stored as JSON
    features = []
    if package.features:
        try:
            features = json.loads(package.features)
        except:
            features = [package.features]  # fallback for non-JSON data
    
    return render_template("package_detail.html", package=package, features=features)

@public_bp.route("/booking-calendar", methods=["GET", "POST"])
def booking_calendar():
    """Booking calendar for clients to schedule consultations and services."""
    if request.method == "POST":
        # Handle booking submission
        booking = Booking(
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            service_type=request.form.get("service_type", ""),
            location=request.form.get("location", "").strip(),
            notes=request.form.get("notes", "").strip(),
            duration_hours=int(request.form.get("duration_hours", 1))
        )
        
        # Handle booking date and time
        booking_date = request.form.get("booking_date")
        start_time = request.form.get("start_time")
        
        if booking_date and start_time:
            try:
                booking.booking_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
                booking.start_time = datetime.strptime(start_time, "%H:%M").time()
                
                # Calculate end time based on duration
                start_datetime = datetime.combine(booking.booking_date, booking.start_time)
                end_datetime = start_datetime + timedelta(hours=booking.duration_hours)
                booking.end_time = end_datetime.time()
                
            except ValueError:
                flash("Invalid date or time format.", "danger")
                return render_template("booking_calendar.html", 
                                     form_data=request.form, 
                                     categories=CORPORATE_CATEGORIES)
        
        # Validate required fields
        if not booking.name or not booking.email or not booking.service_type or not booking_date or not start_time:
            flash("Please fill in all required fields.", "danger")
            return render_template("booking_calendar.html", 
                                 form_data=request.form, 
                                 categories=CORPORATE_CATEGORIES)
        
        # Check for conflicts
        conflicts = Booking.query.filter(
            Booking.booking_date == booking.booking_date,
            Booking.status.in_(["pending", "confirmed"]),
            db.or_(
                db.and_(Booking.start_time <= booking.start_time, Booking.end_time > booking.start_time),
                db.and_(Booking.start_time < booking.end_time, Booking.end_time >= booking.end_time),
                db.and_(booking.start_time <= Booking.start_time, booking.end_time >= Booking.end_time)
            )
        ).first()
        
        if conflicts:
            flash("Sorry, that time slot is already booked. Please select a different time.", "danger")
            return render_template("booking_calendar.html", 
                                 form_data=request.form, 
                                 categories=CORPORATE_CATEGORIES)
        
        # Save booking
        try:
            db.session.add(booking)
            db.session.commit()
            flash("Your booking request has been submitted! We'll confirm your appointment within 24 hours.", "success")
            return redirect(url_for("public.booking_calendar"))
        except Exception as e:
            db.session.rollback()
            flash("There was an error submitting your booking. Please try again.", "danger")
    
    # Get existing bookings for calendar display (next 30 days)
    today = date.today()
    end_date = today + timedelta(days=30)
    
    bookings = Booking.query.filter(
        Booking.booking_date >= today,
        Booking.booking_date <= end_date,
        Booking.status.in_(["pending", "confirmed"])
    ).all()
    
    # Create a calendar data structure
    calendar_data = {}
    current_date = today
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        calendar_data[date_str] = {
            "date": current_date,
            "bookings": [],
            "available_slots": []
        }
        current_date += timedelta(days=1)
    
    # Add bookings to calendar
    for booking in bookings:
        date_str = booking.booking_date.strftime("%Y-%m-%d")
        if date_str in calendar_data:
            calendar_data[date_str]["bookings"].append(booking)
    
    return render_template("booking_calendar.html", 
                         categories=CORPORATE_CATEGORIES,
                         calendar_data=calendar_data,
                         today=today)

@public_bp.route("/api/check-availability")
def check_availability():
    """AJAX endpoint to check time slot availability."""
    booking_date = request.args.get("date")
    start_time = request.args.get("time")
    duration = int(request.args.get("duration", 1))
    
    if not booking_date or not start_time:
        return jsonify({"available": False, "message": "Missing date or time"})
    
    try:
        check_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        check_start_time = datetime.strptime(start_time, "%H:%M").time()
        
        # Calculate end time
        start_datetime = datetime.combine(check_date, check_start_time)
        end_datetime = start_datetime + timedelta(hours=duration)
        check_end_time = end_datetime.time()
        
        # Check for conflicts
        conflicts = Booking.query.filter(
            Booking.booking_date == check_date,
            Booking.status.in_(["pending", "confirmed"]),
            db.or_(
                db.and_(Booking.start_time <= check_start_time, Booking.end_time > check_start_time),
                db.and_(Booking.start_time < check_end_time, Booking.end_time >= check_end_time),
                db.and_(check_start_time <= Booking.start_time, check_end_time >= Booking.end_time)
            )
        ).first()
        
        if conflicts:
            return jsonify({
                "available": False, 
                "message": f"Time slot conflicts with existing booking from {conflicts.time_display}"
            })
        
        return jsonify({"available": True, "message": "Time slot is available"})
        
    except Exception as e:
        return jsonify({"available": False, "message": "Invalid date or time format"})

@public_bp.route("/", endpoint="index")
def home():
    # Get available categories for the navigation
    categories = [c[0] for c in db.session.query(Product.category).distinct() if c[0]]
    
    # Create featured products if they don't exist
    if not Product.query.filter_by(featured=True).first():
        # Sample featured products with video content
        sample_products = [
            Product(
                title="Urban Documentary",
                description="A glimpse into city life through cinematic storytelling",
                price_cents=150000,  # $1,500.00
                media_key="urban_documentary.mp4",
                video_key="urban_documentary.mp4",
                video_thumbnail="urban_documentary_preview.jpg",
                video_duration=180,  # 3 minutes
                category="Documentary",
                client_name="City Arts Council",
                client_testimonial="Beautiful cinematography that captured the essence of our city.",
                featured=True,
                stock=1
            ),
            Product(
                title="Wedding Highlights",
                description="Romantic wedding film capturing special moments",
                price_cents=200000,  # $2,000.00
                media_key="wedding_highlights.mp4",
                video_key="wedding_highlights.mp4",
                video_thumbnail="wedding_highlights_preview.jpg",
                video_duration=240,  # 4 minutes
                category="Wedding",
                client_name="Sarah & James",
                client_testimonial="They captured moments we didn't even know existed. Absolutely amazing!",
                featured=True,
                stock=1
            ),
            Product(
                title="Product Commercial",
                description="High-end product showcase for luxury brand",
                price_cents=180000,  # $1,800.00
                media_key="product_commercial.mp4",
                video_key="product_commercial.mp4",
                video_thumbnail="product_commercial_preview.jpg",
                video_duration=60,  # 1 minute
                category="Commercial",
                client_name="Luxury Brand Co",
                client_testimonial="The quality of the production exceeded our expectations.",
                featured=True,
                stock=1
            )
        ]
        
        for product in sample_products:
            db.session.add(product)
        
        db.session.commit()
    
    # Get featured video products
    featured_products = Product.query.filter_by(featured=True).order_by(Product.created_at.desc()).all()
    return render_template("home.html", available_categories=categories, featured_products=featured_products)

def _build_products_query():
    q          = request.args.get("q", "").strip()
    min_price  = request.args.get("min_price", type=int)
    max_price  = request.args.get("max_price", type=int)
    category   = request.args.get("category", "").strip()
    media_type = request.args.get("media_type", "").strip()

    products_q = Product.query
    if q:
        products_q = products_q.filter(Product.title.ilike(f"%{q}%"))
    if min_price is not None:
        products_q = products_q.filter(Product.price_cents >= min_price * 100)
    if max_price is not None:
        products_q = products_q.filter(Product.price_cents <= max_price * 100)
    if category:
        products_q = products_q.filter_by(category=category)
    if media_type:
        products_q = products_q.filter(Product.mime_type.ilike(f"{media_type}%"))

    filters = {
        "q": q, "min_price": min_price, "max_price": max_price,
        "category": category, "media_type": media_type,
    }
    return products_q, filters

@public_bp.route("/shop")
def shop():
    products_q, filters = _build_products_query()
    products = products_q.order_by(Product.created_at.desc()).all()
    categories  = [c[0] for c in db.session.query(Product.category).distinct() if c[0]]
    media_types = [m[0] for m in db.session.query(Product.mime_type).distinct() if m[0]]
    return render_template(
        "shop.html",
        products=products,
        categories=categories,
        media_types=media_types,
        filters=filters,
    )

@public_bp.route("/about")
def about():
    return render_template("about.html")

@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # Handle contact form submission
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        inquiry_type = request.form.get("inquiry_type", "General")
        company = request.form.get("company", "").strip()
        message = request.form.get("message", "").strip()
        
        # Validate required fields
        if not name or not email or not message:
            flash("Please fill in all required fields (Name, Email, Message).", "danger")
            return render_template("contact.html", form_data=request.form, categories=CORPORATE_CATEGORIES)
        
        # For corporate inquiries, create a quote request instead of just a contact
        if inquiry_type in CORPORATE_CATEGORIES:
            quote_request = QuoteRequest(
                name=name,
                email=email,
                phone=phone,
                company=company,
                service_type=inquiry_type,
                project_description=message
            )
            
            try:
                db.session.add(quote_request)
                db.session.commit()
                flash("Your corporate inquiry has been received! We'll respond within 24 hours with a detailed quote.", "success")
            except Exception as e:
                db.session.rollback()
                flash("There was an error submitting your inquiry. Please try again.", "danger")
        else:
            # For general inquiries, we could create a separate Contact model or handle differently
            # For now, just show a success message
            flash("Thank you for your message! We'll get back to you soon.", "success")
        
        return redirect(url_for("public.contact"))
    
    return render_template("contact.html", categories=CORPORATE_CATEGORIES)

@public_bp.route("/api/products/<int:product_id>/quick-view")
def quick_view(product_id):
    p = Product.query.get_or_404(product_id)
    return render_template("partials/quick_view.html", 
                         product=p,
                         size_options=SIZE_OPTIONS,
                         frame_options=FRAME_OPTIONS)

# -----------------------------
# Video player page
# -----------------------------
@public_bp.route("/video/<int:product_id>")
def video(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.video_key:
        abort(404)
    return render_template("video_player.html", product=product)

# -----------------------------
# Product detail (GET shows page, POST adds to cart)
# -----------------------------
@public_bp.route("/product/<int:product_id>", methods=["GET", "POST"])
def product(product_id):
    p = Product.query.get_or_404(product_id)

    if request.method == "POST":
        size  = request.form.get("size", "20cm x 30cm")
        frame = request.form.get("frame", "No frame")
        qty   = request.form.get("qty", type=int, default=1)
        qty   = 1 if qty is None or qty < 1 else qty

        unit_price = _unit_price_cents(p, size, frame)

        cart = _get_cart()
        # merge with existing same (product,size,frame)
        for item in cart:
            if item["product_id"] == p.id and item["size"] == size and item["frame"] == frame:
                item["qty"] += qty
                _save_cart(cart)
                
                # Return JSON response for AJAX requests
                if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                    cart_count = sum(int(item.get("qty", 1)) for item in cart)
                    return jsonify({
                        'success': True,
                        'message': f'{p.title} added to cart',
                        'cart_count': cart_count
                    })
                
                flash("Added to cart.", "success")
                return redirect(url_for("public.cart"))

        # else push new line
        cart.append({
            "product_id": p.id,
            "title": p.title,
            "size": size,
            "frame": frame,
            "qty": qty,
            "unit_price_cents": unit_price,
            # show image in cart (your files live under static/uploads)
            "image": p.media_key,     # assume Product.media_key is the filename
        })
        _save_cart(cart)
        
        # Return JSON response for AJAX requests
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            cart_count = sum(int(item.get("qty", 1)) for item in _get_cart())
            return jsonify({
                'success': True,
                'message': f'{p.title} added to cart',
                'cart_count': cart_count
            })
        
        flash("Added to cart.", "success")
        return redirect(url_for("public.cart"))

    # GET: show page
    return render_template(
        "product.html",
        product=p,
        size_options=SIZE_OPTIONS,    # dict for select
        frame_options=FRAME_OPTIONS,  # dict for select
    )

# -----------------------------
# Cart pages & actions
# -----------------------------

@public_bp.route("/cart")
def cart():
    cart_raw = session.get("cart", [])
    items = []
    total = 0

    for idx, it in enumerate(cart_raw):
        # basic fields with safe defaults
        pid   = it.get("product_id") or it.get("id")
        qty   = int(it.get("qty", 1))
        size  = it.get("size", "20cm x 30cm")
        frame = it.get("frame", "No frame")

        # skip if product was removed from DB
        p = Product.query.get(pid)
        if not p:
            continue

        # If old cart entry has no unit price, recompute and persist it
        unit = it.get("unit_price_cents")
        if unit is None:
            size_add  = int(SIZE_OPTIONS.get(size, 0))
            frame_add = int(FRAME_OPTIONS.get(frame, 0))
            unit = int(p.price_cents) + size_add + frame_add
            it["unit_price_cents"] = unit  # normalize old entry

        subtotal = int(unit) * qty
        total += subtotal

        items.append({
            "idx": idx,
            "title": p.title,
            "image": p.media_key,                # stored under static/uploads/
            "size": size,
            "frame": frame,
            "qty": qty,
            "unit_price_cents": unit,
            "subtotal_cents": subtotal,
        })

    # Save normalized cart back into the session
    session["cart"] = cart_raw
    session.modified = True

    return render_template("cart.html", items=items, total=total)

@public_bp.route("/cart/inc/<int:item_idx>", methods=["POST"])
def cart_inc(item_idx):
    cart = _get_cart()
    if 0 <= item_idx < len(cart):
        cart[item_idx]["qty"] += 1
        _save_cart(cart)
    
    # Return JSON response for AJAX requests
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        total = _cart_totals()
        cart_count = sum(int(item.get("qty", 1)) for item in cart)
        return jsonify({
            'success': True,
            'qty': cart[item_idx]["qty"] if 0 <= item_idx < len(cart) else 0,
            'subtotal': (cart[item_idx]["qty"] * cart[item_idx]["unit_price_cents"]) if 0 <= item_idx < len(cart) else 0,
            'total': total,
            'cart_count': cart_count
        })
    
    return redirect(url_for("public.cart"))

@public_bp.route("/cart/dec/<int:item_idx>", methods=["POST"])
def cart_dec(item_idx):
    cart = _get_cart()
    if 0 <= item_idx < len(cart):
        cart[item_idx]["qty"] = max(1, int(cart[item_idx]["qty"]) - 1)
        _save_cart(cart)
    
    # Return JSON response for AJAX requests
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        total = _cart_totals()
        cart_count = sum(int(item.get("qty", 1)) for item in cart)
        return jsonify({
            'success': True,
            'qty': cart[item_idx]["qty"] if 0 <= item_idx < len(cart) else 0,
            'subtotal': (cart[item_idx]["qty"] * cart[item_idx]["unit_price_cents"]) if 0 <= item_idx < len(cart) else 0,
            'total': total,
            'cart_count': cart_count
        })
    
    return redirect(url_for("public.cart"))

@public_bp.route("/cart/del/<int:item_idx>", methods=["POST"])
def cart_del(item_idx):
    cart = _get_cart()
    removed_item = None
    if 0 <= item_idx < len(cart):
        removed_item = cart.pop(item_idx)
        _save_cart(cart)
    
    # Return JSON response for AJAX requests
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        total = _cart_totals()
        cart_count = sum(int(item.get("qty", 1)) for item in cart)
        return jsonify({
            'success': True,
            'removed_item': removed_item.get('title', 'Item') if removed_item else 'Item',
            'total': total,
            'cart_count': cart_count,
            'cart_empty': len(cart) == 0
        })
    
    return redirect(url_for("public.cart"))

# -----------------------------
# Checkout → Confirmation (very simple demo flow)
# -----------------------------
@public_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart_raw = session.get("cart", [])
    if not cart_raw:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("public.shop"))

    # Process cart items same as in cart() route
    items = []
    total = 0

    for idx, it in enumerate(cart_raw):
        # basic fields with safe defaults
        pid   = it.get("product_id") or it.get("id")
        qty   = int(it.get("qty", 1))
        size  = it.get("size", "20cm x 30cm")
        frame = it.get("frame", "No frame")

        # skip if product was removed from DB
        p = Product.query.get(pid)
        if not p:
            continue

        # If old cart entry has no unit price, recompute and persist it
        unit = it.get("unit_price_cents")
        if unit is None:
            size_add  = int(SIZE_OPTIONS.get(size, 0))
            frame_add = int(FRAME_OPTIONS.get(frame, 0))
            unit = int(p.price_cents) + size_add + frame_add
            it["unit_price_cents"] = unit  # normalize old entry

        subtotal = int(unit) * qty
        total += subtotal

        items.append({
            "idx": idx,
            "title": p.title,
            "image": p.media_key,
            "size": size,
            "frame": frame,
            "qty": qty,
            "unit_price_cents": unit,
            "subtotal_cents": subtotal,
        })

    # Save normalized cart back into the session
    session["cart"] = cart_raw
    session.modified = True

    if request.method == "POST":
        # Get form data
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        
        # Validate required fields
        errors = []
        if not name:
            errors.append("Full name is required")
        if not address:
            errors.append("Shipping address is required")
        if not email:
            errors.append("Email address is required")
            
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("checkout.html", total=total, items=items, 
                                 name=name, address=address, email=email, phone=phone)
        
        # Create Order record in database
        try:
            order = Order(
                email=email,
                amount_cents=total,
                currency="sgd",
                status="pending"
            )
            
            # Link to user if logged in
            if session.get("user_id"):
                order.user_id = session["user_id"]
            
            db.session.add(order)
            db.session.flush()  # Get the order ID
            
            # Create OrderItem records
            for idx, item in enumerate(items):
                # Get the original cart item to find product_id
                cart_item = cart_raw[idx]
                product_id = cart_item.get("product_id") or cart_item.get("id")
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=item["qty"],
                    unit_price_cents=item["unit_price_cents"]
                )
                db.session.add(order_item)
            
            db.session.commit()
            
            # Clear cart and redirect to confirmation
            session["cart"] = []
            session.modified = True
            return redirect(url_for("public.confirmation", order_no=f"ORD{order.id:05d}"))
            
        except Exception as e:
            db.session.rollback()
            flash("There was an error processing your order. Please try again.", "danger")
            return render_template("checkout.html", total=total, items=items, 
                                 name=name, address=address, email=email, phone=phone)

    # GET: show checkout form
    # Pre-fill form for logged-in users
    user_data = {}
    if session.get("user_id"):
        user = db.session.get(User, session["user_id"])
        if user:
            user_data = {
                'email': user.email,
                'name': getattr(user, 'name', ''),
                'phone': getattr(user, 'phone', ''),
                'address': getattr(user, 'address', '')
            }
    
    return render_template("checkout.html", total=total, items=items, **user_data)

@public_bp.route("/confirmation")
def confirmation():
    order_no = request.args.get("order_no")
    if not order_no:
        return redirect(url_for("public.shop"))
    return render_template("confirmation.html", order_no=order_no)


@public_bp.app_context_processor
def inject_cart_count():
    # Get cart count
    cart = session.get("cart", [])
    try:
        count = sum(int(item.get("qty", 1)) for item in cart)
    except Exception:
        count = 0
        
    # Get available categories
    categories = [c[0] for c in db.session.query(Product.category).distinct() if c[0]]
    
    return {
        "cart_count": count,
        "available_categories": categories
    }

# -----------------------------
# User Profile and Orders (placeholder routes)
# -----------------------------
@public_bp.route("/orders")
def orders():
    """User orders page"""
    if not session.get("user_id"):
        flash("Please log in to view your orders.", "warning")
        return redirect(url_for("auth.auth"))
    
    user = db.session.get(User, session["user_id"])
    if not user:
        flash("User not found. Please log in again.", "error")
        return redirect(url_for("auth.auth"))
    
    # Get user's orders
    user_orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    
    return render_template("orders.html", orders=user_orders)

@public_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """User profile page"""
    if not session.get("user_id"):
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for("auth.auth"))
    
    # Get the current user
    user = db.session.get(User, session["user_id"])
    if not user:
        flash("User not found. Please log in again.", "error")
        return redirect(url_for("auth.auth"))
    
    if request.method == "POST":
        # Handle profile updates
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        
        # Validate and update email if changed
        if email and email != user.email:
            # Check if email is already taken
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email address is already in use.", "danger")
            else:
                user.email = email
                flash("Email updated successfully.", "success")
        
        # Update password if provided
        if password:
            user.set_password(password)
            flash("Password updated successfully.", "success")
        
        # Save changes
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating your profile.", "danger")
        
        return redirect(url_for("public.profile"))
    
    # GET request - show profile page
    # Get user's orders
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    
    return render_template("profile.html", user=user, orders=orders)
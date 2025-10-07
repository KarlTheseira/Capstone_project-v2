# Load environment variables first, before any other imports
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, session, render_template, send_from_directory
from flask_migrate import Migrate
from models import db, Product, User, Order, OrderItem
from config import Config
from utils.google_drive import drive_service
from utils.local_storage import local_storage_service
import logging
from datetime import timedelta
import os

# Import blueprints
from routes.public import public_bp
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.upload import upload_bp
from routes.gdrive import gdrive_bp
from routes.payment import payment_bp
from routes.admin_videos import admin_videos_bp


app = Flask(__name__)
app.config.from_object(Config)

# Enhanced session configuration for development stability
app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP in development
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Long session for development
app.config['SESSION_COOKIE_NAME'] = 'flash_studio_session'

db.init_app(app)
migrate = Migrate(app, db)

## --- Storage Backend Selection (local or drive) ---
backend = app.config.get('STORAGE_BACKEND', 'local')
if backend == 'drive':
    folder_id_env = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    if folder_id_env:
        app.config['GOOGLE_DRIVE_FOLDER_ID'] = folder_id_env
    else:
        logging.warning("GOOGLE_DRIVE_FOLDER_ID not set in environment at app startup (drive backend selected)")
    logging.info("[storage] Initializing Google Drive backend (folder id=%s)", app.config.get('GOOGLE_DRIVE_FOLDER_ID'))
    drive_service.init_app(app)
    app.extensions['active_storage'] = drive_service
else:
    logging.info("[storage] Using local storage backend")
    app.extensions['active_storage'] = local_storage_service
app.config['ACTIVE_STORAGE_BACKEND'] = backend

# Register blueprints
app.register_blueprint(public_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(gdrive_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(admin_videos_bp)

# -------------------------------------------------------------
# Diagnostic Google Drive routes (can be removed in production)
# -------------------------------------------------------------
from flask import jsonify
from werkzeug.datastructures import FileStorage
import io

@app.route('/drive/status', methods=['GET'])
def drive_status():
    """Return current Google Drive integration status and sample listing."""
    try:
        configured = drive_service.is_configured()
        folder_id = getattr(drive_service, 'folder_id', None)
        sample = None
        error = None
        if configured:
            ok, result = drive_service.list_files(limit=5)
            if ok:
                sample = result.get('files', [])
            else:
                error = result.get('error')
        return jsonify({
            'configured': configured,
            'folder_id': folder_id,
            'sample_files': sample,
            'error': error
        }), 200 if configured else 500
    except Exception as e:
        logging.exception("Drive status check failed")
        return jsonify({'configured': False, 'error': str(e)}), 500

@app.route('/drive/upload-test', methods=['POST'])
def drive_upload_test():
    """Upload a small in-memory text file to Drive for validation."""
    if not drive_service.is_configured():
        return jsonify({'error': 'Drive not configured'}), 500
    try:
        content = f"FlashStudio diagnostic upload test at {__import__('datetime').datetime.utcnow().isoformat()}".encode('utf-8')
        stream = io.BytesIO(content)
        file_obj = FileStorage(stream=stream, filename='diagnostic_test.txt', content_type='text/plain')
        ok, result = drive_service.upload_file(file_obj)
        if ok:
            return jsonify({'success': True, 'file': result}), 200
        return jsonify({'success': False, 'error': result.get('error')}), 500
    except Exception as e:
        logging.exception("Diagnostic upload failed")
        return jsonify({'success': False, 'error': str(e)}), 500

# Media serving route
@app.route('/media/<path:filename>')
def media(filename):
    """Serve media files from the uploads directory"""
    return send_from_directory('static/uploads', filename)

# Context processor for templates
@app.context_processor
def inject_user():
    """Inject current user and admin status into template context"""
    current_user = None
    current_admin = None
    if session.get("user_id"):
        current_user = db.session.get(User, session["user_id"])
    if session.get("admin") or session.get("admin_logged_in"):
        current_admin = True
    return dict(current_user=current_user, current_admin=current_admin)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return '<h1>Page Not Found</h1><p>The page you are looking for does not exist.</p>', 404

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    db.session.rollback()
    return '<h1>Internal Server Error</h1><p>Something went wrong.</p>', 500

def init_db():
    """Initialize database with sample data if empty"""
    with app.app_context():
        # Only create tables if they don't exist
        db.create_all()
        
        # Check if we need to add some initial data
        if Product.query.count() == 0:
            # Add some sample products with video content for showreel
            sample_products = [
                Product(
                    title="Urban Documentary",
                    description="A glimpse into city life through cinematic storytelling",
                    price_cents=150000,  # $1,500.00
                    media_key="urban_doc_thumb.jpg",
                    video_key="urban_documentary.mp4",
                    video_thumbnail="urban_doc_preview.jpg",
                    video_duration=180,  # 3 minutes
                    category="Documentary",
                    client_name="City Arts Council",
                    featured=True,
                    stock=1
                ),
                Product(
                    title="Wedding Highlights",
                    description="Romantic wedding film capturing special moments",
                    price_cents=200000,  # $2,000.00
                    media_key="wedding_thumb.jpg",
                    video_key="wedding_highlights.mp4",
                    video_thumbnail="wedding_preview.jpg",
                    video_duration=240,  # 4 minutes
                    category="Wedding",
                    client_name="Sarah & James",
                    client_testimonial="Beautifully captured our special day!",
                    featured=True,
                    stock=1
                ),
                Product(
                    title="Product Commercial",
                    description="High-end product showcase for luxury brand",
                    price_cents=180000,  # $1,800.00
                    media_key="product_thumb.jpg",
                    video_key="product_commercial.mp4",
                    video_thumbnail="product_preview.jpg",
                    video_duration=60,  # 1 minute
                    category="Commercial",
                    client_name="Luxury Brand Co",
                    client_testimonial="Exceeded our expectations!",
                    featured=True,
                    stock=1
                )
            ]
            
            for product in sample_products:
                db.session.add(product)
            
            db.session.commit()

if __name__ == "__main__":
    # Initialize database with sample data if needed
    init_db()
    
    # Run with debug controlled by environment variable
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode, host='127.0.0.1', port=5001)

@app.get("/healthz") 
def healthz(): 
    return {"ok": True}, 200


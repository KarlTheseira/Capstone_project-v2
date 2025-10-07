from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Product, db
from utils.media import save_media
from routes.admin import require_admin

admin_videos_bp = Blueprint('admin_videos', __name__, url_prefix='/admin/videos')

@admin_videos_bp.route('/')
def videos_dashboard():
    """Video management dashboard for featured work section"""
    require_admin()
    
    # Get all video products (featured work)
    video_products = Product.query.filter(
        Product.video_key.isnot(None),
        Product.video_key != ''
    ).order_by(Product.featured.desc(), Product.created_at.desc()).all()
    
    # Get featured videos specifically for homepage
    featured_videos = Product.query.filter_by(featured=True).filter(
        Product.video_key.isnot(None),
        Product.video_key != ''
    ).order_by(Product.created_at.desc()).all()
    
    return render_template('admin_homepage_videos.html', 
                         video_products=video_products,
                         featured_videos=featured_videos)

@admin_videos_bp.route('/add', methods=['GET', 'POST'])
def add_video():
    """Add a new video to the featured work section"""
    require_admin()
    
    if request.method == 'POST':
        try:
            # Create new product for video
            product = Product()
            
            # Basic information
            product.title = request.form.get('title', '').strip()
            product.description = request.form.get('description', '').strip()
            product.client_name = request.form.get('client_name', '').strip()
            product.client_testimonial = request.form.get('client_testimonial', '').strip()
            
            # Video duration (convert minutes:seconds to total seconds)
            duration_str = request.form.get('duration', '')
            if duration_str and ':' in duration_str:
                try:
                    minutes, seconds = map(int, duration_str.split(':'))
                    product.video_duration = minutes * 60 + seconds
                except ValueError:
                    pass
            
            # Set as featured for homepage
            product.featured = request.form.get('featured') == 'on'
            
            # Set category as video/portfolio
            product.category = 'Video Portfolio'
            
            # Handle video file upload
            video_file = request.files.get('video_file')
            if video_file and video_file.filename:
                video_key, video_url = save_media(video_file)
                product.video_key = video_key
                product.media_key = video_key  # Also set as main media
                product.mime_type = video_file.mimetype
            else:
                flash('Video file is required', 'error')
                return redirect(url_for('admin_videos.videos_dashboard'))
            
            # Handle thumbnail upload
            thumbnail_file = request.files.get('thumbnail_file')
            if thumbnail_file and thumbnail_file.filename:
                thumbnail_key, thumbnail_url = save_media(thumbnail_file)
                product.video_thumbnail = thumbnail_key
                product.thumbnail_key = thumbnail_key
            
            # Set default price and stock (not really used for portfolio videos)
            product.price_cents = 0
            product.stock = 1
            
            db.session.add(product)
            db.session.commit()
            
            flash(f'Video "{product.title}" added successfully!', 'success')
            return redirect(url_for('admin_videos.videos_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding video: {str(e)}', 'error')
            return redirect(url_for('admin_videos.videos_dashboard'))
    
    return render_template('admin_homepage_videos.html')

@admin_videos_bp.route('/edit/<int:video_id>', methods=['GET', 'POST'])
def edit_video(video_id):
    """Edit an existing video"""
    require_admin()
    
    product = Product.query.get_or_404(video_id)
    
    if request.method == 'POST':
        try:
            # Update basic information
            product.title = request.form.get('title', '').strip()
            product.description = request.form.get('description', '').strip()
            product.client_name = request.form.get('client_name', '').strip()
            product.client_testimonial = request.form.get('client_testimonial', '').strip()
            
            # Update video duration
            duration_str = request.form.get('duration', '')
            if duration_str and ':' in duration_str:
                try:
                    minutes, seconds = map(int, duration_str.split(':'))
                    product.video_duration = minutes * 60 + seconds
                except ValueError:
                    pass
            
            # Update featured status
            product.featured = request.form.get('featured') == 'on'
            
            # Handle video file replacement
            video_file = request.files.get('video_file')
            if video_file and video_file.filename:
                video_key, video_url = save_media(video_file)
                product.video_key = video_key
                product.media_key = video_key
                product.mime_type = video_file.mimetype
            
            # Handle thumbnail replacement
            thumbnail_file = request.files.get('thumbnail_file')
            if thumbnail_file and thumbnail_file.filename:
                thumbnail_key, thumbnail_url = save_media(thumbnail_file)
                product.video_thumbnail = thumbnail_key
                product.thumbnail_key = thumbnail_key
            
            db.session.commit()
            
            flash(f'Video "{product.title}" updated successfully!', 'success')
            return redirect(url_for('admin_videos.videos_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating video: {str(e)}', 'error')
    
    return redirect(url_for('admin_videos.videos_dashboard'))

@admin_videos_bp.route('/delete/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    """Delete a video from featured work"""
    require_admin()
    
    try:
        product = Product.query.get_or_404(video_id)
        video_title = product.title
        
        db.session.delete(product)
        db.session.commit()
        
        flash(f'Video "{video_title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting video: {str(e)}', 'error')
    
    return redirect(url_for('admin_videos.videos_dashboard'))

@admin_videos_bp.route('/toggle-featured/<int:video_id>', methods=['POST'])
def toggle_featured(video_id):
    """Toggle featured status of a video"""
    require_admin()
    
    try:
        product = Product.query.get_or_404(video_id)
        product.featured = not product.featured
        db.session.commit()
        
        status = 'featured' if product.featured else 'unfeatured'
        flash(f'Video "{product.title}" {status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating video: {str(e)}', 'error')
    
    return redirect(url_for('admin_videos.videos_dashboard'))

@admin_videos_bp.route('/reorder', methods=['POST'])
def reorder_videos():
    """Reorder featured videos for homepage display"""
    require_admin()
    
    try:
        video_ids = request.json.get('video_ids', [])
        
        for index, video_id in enumerate(video_ids):
            product = Product.query.get(video_id)
            if product:
                # Use a custom order field or update timestamp
                # For now, we'll use the ID ordering
                pass
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

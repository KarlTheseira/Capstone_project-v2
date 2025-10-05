"""
Admin route for managing homepage videos
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from models import db, Product
from werkzeug.utils import secure_filename
import os
from datetime import datetime

admin_videos_bp = Blueprint('admin_videos', __name__)

@admin_videos_bp.route('/admin/homepage-videos')
def manage_homepage_videos():
    """Admin page to manage homepage videos"""
    
    # Get current featured videos (the 3 tabs)
    featured_videos = Product.query.filter_by(featured=True).order_by(Product.created_at.desc()).all()
    
    return render_template('admin_homepage_videos.html', featured_videos=featured_videos)

@admin_videos_bp.route('/admin/update-hero-video', methods=['POST'])
def update_hero_video():
    """Update the main hero background video"""
    
    try:
        if 'hero_video' not in request.files:
            flash('No video file provided', 'error')
            return redirect(url_for('admin_videos.manage_homepage_videos'))
        
        file = request.files['hero_video']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('admin_videos.manage_homepage_videos'))
        
        if file and file.filename.lower().endswith(('.mp4', '.webm', '.mov')):
            # Save the new hero video
            filename = secure_filename('hero.mp4')  # Always name it hero.mp4
            file_path = os.path.join('static/video', filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            file.save(file_path)
            flash('Hero video updated successfully!', 'success')
        else:
            flash('Invalid video format. Please use MP4, WebM, or MOV.', 'error')
    
    except Exception as e:
        flash(f'Error updating hero video: {str(e)}', 'error')
    
    return redirect(url_for('admin_videos.manage_homepage_videos'))

@admin_videos_bp.route('/admin/update-featured-video/<int:product_id>', methods=['POST'])
def update_featured_video(product_id):
    """Update one of the featured videos (tabs)"""
    
    try:
        product = Product.query.get_or_404(product_id)
        
        # Update video file
        if 'video_file' in request.files and request.files['video_file'].filename:
            video_file = request.files['video_file']
            if video_file.filename.lower().endswith(('.mp4', '.webm', '.mov')):
                video_filename = f"{secure_filename(product.title.lower().replace(' ', '_'))}.mp4"
                video_path = os.path.join('static/uploads', video_filename)
                video_file.save(video_path)
                product.video_key = video_filename
        
        # Update thumbnail
        if 'thumbnail_file' in request.files and request.files['thumbnail_file'].filename:
            thumb_file = request.files['thumbnail_file']
            if thumb_file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                thumb_filename = f"{secure_filename(product.title.lower().replace(' ', '_'))}_preview.jpg"
                thumb_path = os.path.join('static/uploads', thumb_filename)
                thumb_file.save(thumb_path)
                product.video_thumbnail = thumb_filename
        
        # Update text fields
        if request.form.get('title'):
            product.title = request.form['title']
        if request.form.get('description'):
            product.description = request.form['description']
        if request.form.get('client_name'):
            product.client_name = request.form['client_name']
        if request.form.get('duration'):
            try:
                # Convert MM:SS to seconds
                duration_str = request.form['duration']
                if ':' in duration_str:
                    minutes, seconds = map(int, duration_str.split(':'))
                    product.video_duration = minutes * 60 + seconds
                else:
                    product.video_duration = int(duration_str)
            except:
                pass
        
        db.session.commit()
        flash(f'Updated "{product.title}" successfully!', 'success')
    
    except Exception as e:
        flash(f'Error updating video: {str(e)}', 'error')
    
    return redirect(url_for('admin_videos.manage_homepage_videos'))

@admin_videos_bp.route('/admin/add-featured-video', methods=['POST'])
def add_featured_video():
    """Add a new featured video to the homepage tabs"""
    
    try:
        # Check if we already have 3 featured videos
        current_count = Product.query.filter_by(featured=True).count()
        if current_count >= 6:  # Allow up to 6 featured videos
            flash('Maximum of 6 featured videos allowed. Please remove one first.', 'warning')
            return redirect(url_for('admin_videos.manage_homepage_videos'))
        
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('admin_videos.manage_homepage_videos'))
        
        # Create new product
        new_product = Product(
            title=title,
            description=description or '',
            price_cents=0,  # Portfolio items have no price
            media_key='',  # Will be set when video is uploaded
            stock=1,
            featured=True,
            category='portfolio',
            client_name=request.form.get('client_name', ''),
            created_at=datetime.utcnow()
        )
        
        # Handle video upload
        if 'video_file' in request.files and request.files['video_file'].filename:
            video_file = request.files['video_file']
            if video_file.filename.lower().endswith(('.mp4', '.webm', '.mov')):
                video_filename = f"{secure_filename(title.lower().replace(' ', '_'))}.mp4"
                video_path = os.path.join('static/uploads', video_filename)
                video_file.save(video_path)
                new_product.video_key = video_filename
                new_product.media_key = video_filename
        
        # Handle thumbnail upload
        if 'thumbnail_file' in request.files and request.files['thumbnail_file'].filename:
            thumb_file = request.files['thumbnail_file']
            if thumb_file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                thumb_filename = f"{secure_filename(title.lower().replace(' ', '_'))}_preview.jpg"
                thumb_path = os.path.join('static/uploads', thumb_filename)
                thumb_file.save(thumb_path)
                new_product.video_thumbnail = thumb_filename
        
        # Set duration
        duration_str = request.form.get('duration')
        if duration_str:
            try:
                if ':' in duration_str:
                    minutes, seconds = map(int, duration_str.split(':'))
                    new_product.video_duration = minutes * 60 + seconds
                else:
                    new_product.video_duration = int(duration_str)
            except:
                new_product.video_duration = 120  # Default 2 minutes
        
        db.session.add(new_product)
        db.session.commit()
        
        flash(f'Added new featured video "{title}" successfully!', 'success')
    
    except Exception as e:
        flash(f'Error adding video: {str(e)}', 'error')
    
    return redirect(url_for('admin_videos.manage_homepage_videos'))

@admin_videos_bp.route('/admin/remove-featured-video/<int:product_id>', methods=['POST'])
def remove_featured_video(product_id):
    """Remove a video from featured videos"""
    
    try:
        product = Product.query.get_or_404(product_id)
        
        # Just unfeatured instead of deleting
        product.featured = False
        db.session.commit()
        
        flash(f'Removed "{product.title}" from homepage', 'success')
    
    except Exception as e:
        flash(f'Error removing video: {str(e)}', 'error')
    
    return redirect(url_for('admin_videos.manage_homepage_videos'))
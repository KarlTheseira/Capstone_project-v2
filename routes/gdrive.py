"""
Google Drive video management routes
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from models import db, Product
from utils.google_drive import drive_service
from werkzeug.utils import secure_filename
import os
import tempfile

gdrive_bp = Blueprint('gdrive', __name__)

@gdrive_bp.route('/admin/gdrive-videos')
def manage_videos():
    """Admin page to manage Google Drive videos"""
    
    # Check if Google Drive is configured
    if not drive_service.is_configured():
        flash('Google Drive is not configured. Please set up your credentials.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Get all products with videos
    products = Product.query.filter(
        db.or_(Product.video_key.isnot(None), Product.google_drive_video_id.isnot(None))
    ).all()
    
    # Get Google Drive videos
    drive_videos = drive_service.list_videos()
    
    return render_template('admin_gdrive_videos.html', 
                         products=products, 
                         drive_videos=drive_videos)

@gdrive_bp.route('/admin/upload-to-gdrive/<int:product_id>', methods=['POST'])
def upload_to_gdrive(product_id):
    """Upload a product's local video to Google Drive"""
    
    if not drive_service.is_configured():
        return jsonify({'success': False, 'error': 'Google Drive not configured'})
    
    product = Product.query.get_or_404(product_id)
    
    if not product.video_key:
        return jsonify({'success': False, 'error': 'No local video found'})
    
    try:
        # Path to local video file
        video_path = os.path.join('static/uploads', product.video_key)
        
        if not os.path.exists(video_path):
            return jsonify({'success': False, 'error': 'Local video file not found'})
        
        # Upload to Google Drive
        filename = f"{secure_filename(product.title)}.mp4"
        result = drive_service.upload_video(video_path, filename, product.title)
        
        if result['success']:
            # Update product with Google Drive info
            product.google_drive_video_id = result['file_id']
            product.google_drive_video_url = drive_service.get_streaming_url(result['file_id'])
            product.video_hosting_type = 'google_drive'
            
            db.session.commit()
            
            flash(f'Successfully uploaded "{product.title}" to Google Drive!', 'success')
            return jsonify({
                'success': True, 
                'file_id': result['file_id'],
                'streaming_url': product.google_drive_video_url
            })
        else:
            return jsonify({'success': False, 'error': result['error']})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@gdrive_bp.route('/admin/upload-new-to-gdrive', methods=['POST'])
def upload_new_to_gdrive():
    """Upload a new video file directly to Google Drive"""
    
    if not drive_service.is_configured():
        return jsonify({'success': False, 'error': 'Google Drive not configured'})
    
    try:
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description', '')
        
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'})
        
        # Get uploaded file
        if 'video_file' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'})
        
        video_file = request.files['video_file']
        
        if video_file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Check file type
        if not video_file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            return jsonify({'success': False, 'error': 'Invalid video format'})
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            video_file.save(temp_file.name)
            
            # Upload to Google Drive
            filename = f"{secure_filename(title)}.mp4"
            result = drive_service.upload_video(temp_file.name, filename, title)
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            if result['success']:
                # Create new product entry
                new_product = Product(
                    title=title,
                    description=description,
                    price_cents=0,  # Portfolio item
                    media_key='',  # No local media
                    google_drive_video_id=result['file_id'],
                    google_drive_video_url=drive_service.get_streaming_url(result['file_id']),
                    video_hosting_type='google_drive',
                    category='portfolio',
                    featured=True,
                    stock=1
                )
                
                db.session.add(new_product)
                db.session.commit()
                
                flash(f'Successfully uploaded "{title}" to Google Drive and created product!', 'success')
                return jsonify({
                    'success': True, 
                    'product_id': new_product.id,
                    'file_id': result['file_id']
                })
            else:
                return jsonify({'success': False, 'error': result['error']})
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@gdrive_bp.route('/admin/switch-to-gdrive/<int:product_id>', methods=['POST'])
def switch_to_gdrive(product_id):
    """Switch a product to use Google Drive for video hosting"""
    
    product = Product.query.get_or_404(product_id)
    
    if not product.google_drive_video_id:
        return jsonify({'success': False, 'error': 'No Google Drive video ID found'})
    
    try:
        product.video_hosting_type = 'google_drive'
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Switched "{product.title}" to Google Drive hosting'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@gdrive_bp.route('/admin/switch-to-local/<int:product_id>', methods=['POST'])
def switch_to_local(product_id):
    """Switch a product to use local video hosting"""
    
    product = Product.query.get_or_404(product_id)
    
    if not product.video_key:
        return jsonify({'success': False, 'error': 'No local video file found'})
    
    try:
        product.video_hosting_type = 'local'
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Switched "{product.title}" to local hosting'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@gdrive_bp.route('/admin/delete-gdrive-video/<int:product_id>', methods=['POST'])
def delete_gdrive_video(product_id):
    """Delete a video from Google Drive"""
    
    if not drive_service.is_configured():
        return jsonify({'success': False, 'error': 'Google Drive not configured'})
    
    product = Product.query.get_or_404(product_id)
    
    if not product.google_drive_video_id:
        return jsonify({'success': False, 'error': 'No Google Drive video ID found'})
    
    try:
        # Delete from Google Drive
        result = drive_service.delete_file(product.google_drive_video_id)
        
        if result['success']:
            # Clear Google Drive fields
            product.google_drive_video_id = None
            product.google_drive_video_url = None
            
            # Switch back to local if available
            if product.video_key:
                product.video_hosting_type = 'local'
            else:
                product.video_hosting_type = None
                
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'Deleted "{product.title}" from Google Drive'})
        else:
            return jsonify({'success': False, 'error': result['error']})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
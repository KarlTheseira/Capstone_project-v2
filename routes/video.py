import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, send_file
from models import Product, db
from utils.video import create_video

video_bp = Blueprint('video', __name__, url_prefix='/video')

def init_videos():
    """Initialize video content if not exists."""
    # Create video directories if they don't exist
    os.makedirs('static/video', exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)
    
    # Create hero video if it doesn't exist
    hero_path = 'static/video/hero.mp4'
    if not os.path.exists(hero_path):
        hero_config = {
            'duration': 10,
            'style': 'waves',
            'text': 'Flash Studio',
            'colors': {
                'primary': (64, 32, 16),    # Dark blue
                'secondary': (32, 16, 8),    # Darker blue
                'text': (255, 255, 255),     # White
                'shadow': (0, 0, 0)          # Black
            }
        }
        create_video(hero_path, hero_config)
    
    # Create sample videos if they don't exist
    sample_videos = [
        {
            'path': 'static/uploads/urban_documentary.mp4',
            'thumb': 'static/uploads/urban_documentary_preview.jpg',
            'config': {
                'duration': 10,
                'style': 'gradient',
                'text': 'Urban Documentary'
            }
        },
        {
            'path': 'static/uploads/wedding_highlights.mp4',
            'thumb': 'static/uploads/wedding_highlights_preview.jpg',
            'config': {
                'duration': 10,
                'style': 'particles',
                'text': 'Wedding Highlights'
            }
        },
        {
            'path': 'static/uploads/product_commercial.mp4',
            'thumb': 'static/uploads/product_commercial_preview.jpg',
            'config': {
                'duration': 10,
                'style': 'waves',
                'text': 'Product Commercial'
            }
        }
    ]
    
    for video in sample_videos:
        if not os.path.exists(video['path']):
            create_video(video['path'], video['config'])
            
            # Create thumbnail
            import cv2
            cap = cv2.VideoCapture(video['path'])
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(video['thumb'], frame)
            cap.release()

@video_bp.route('/play/<int:video_id>')
def play(video_id):
    """Stream a video file with optimized headers and error handling."""
    try:
        video = Product.query.get_or_404(video_id)
        if not video.video_key:
            flash('Video not found or not available', 'error')
            abort(404)
        
        video_path = os.path.join('static/uploads', video.video_key)
        if not os.path.exists(video_path):
            flash(f'Video file not found: {video.video_key}', 'error')
            abort(404)
        
        # Get file stats for better header information
        import os
        file_stats = os.stat(video_path)
        file_size = file_stats.st_size
        
        # Stream the video file with enhanced headers
        response = send_file(
            video_path,
            mimetype='video/mp4',
            as_attachment=False,
            conditional=True,  # Enable range requests for proper video streaming
            download_name=f"{video.title}.mp4"
        )
        
        # Enhanced headers for better video streaming
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Content-Type'] = 'video/mp4'
        
        # Caching headers for better performance
        response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
        response.headers['ETag'] = f'"{video_id}-{int(file_stats.st_mtime)}"'
        
        # Cross-origin headers for better compatibility
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Range'
        
        return response
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Video streaming error for video {video_id}: {str(e)}')
        abort(500)

@video_bp.route('/direct/<int:video_id>')
def direct(video_id):
    """Direct video file serving via static files."""
    try:
        video = Product.query.get_or_404(video_id)
        if not video.video_key:
            abort(404)
        
        # Check if file exists before redirecting
        video_path = os.path.join('static/uploads', video.video_key)
        if not os.path.exists(video_path):
            abort(404)
        
        # Redirect to static file serving
        from flask import redirect, url_for
        return redirect(url_for('static', filename=f'uploads/{video.video_key}'))
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Direct video access error for video {video_id}: {str(e)}')
        abort(500)

@video_bp.route('/health/<int:video_id>')
def health(video_id):
    """Check if video file is available and accessible."""
    try:
        video = Product.query.get_or_404(video_id)
        if not video.video_key:
            return {'status': 'error', 'message': 'No video key'}, 404
        
        video_path = os.path.join('static/uploads', video.video_key)
        if not os.path.exists(video_path):
            return {'status': 'error', 'message': 'Video file not found'}, 404
        
        # Get file information
        import os
        file_stats = os.stat(video_path)
        
        return {
            'status': 'ok',
            'video_id': video_id,
            'title': video.title,
            'filename': video.video_key,
            'size': file_stats.st_size,
            'size_mb': round(file_stats.st_size / (1024 * 1024), 2),
            'modified': int(file_stats.st_mtime)
        }, 200
        
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@video_bp.route('/info/<int:video_id>')
def info(video_id):
    """Get detailed video information."""
    try:
        video = Product.query.get_or_404(video_id)
        
        video_info = {
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'duration': video.video_duration,
            'duration_display': getattr(video, 'duration_display', 'Unknown'),
            'has_video': bool(video.video_key),
            'video_key': video.video_key,
            'thumbnail': video.video_thumbnail,
            'client': video.client_name
        }
        
        if video.video_key:
            video_path = os.path.join('static/uploads', video.video_key)
            if os.path.exists(video_path):
                file_stats = os.stat(video_path)
                video_info['file_size'] = file_stats.st_size
                video_info['file_size_mb'] = round(file_stats.st_size / (1024 * 1024), 2)
                video_info['file_available'] = True
            else:
                video_info['file_available'] = False
        
        return video_info, 200
        
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
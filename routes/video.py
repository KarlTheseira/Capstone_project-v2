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
    """Stream a video file."""
    video = Product.query.get_or_404(video_id)
    if not video.video_key:
        abort(404)
    
    video_path = os.path.join('static/uploads', video.video_key)
    if not os.path.exists(video_path):
        abort(404)
    
    # Stream the video file
    return send_file(
        video_path,
        mimetype='video/mp4',
        as_attachment=False,
        conditional=True  # Enable range requests for proper video streaming
    )
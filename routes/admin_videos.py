from flask import (
	Blueprint, render_template, redirect, url_for, flash, abort,
	request, session, current_app
)
from models import Product, db
from werkzeug.utils import secure_filename
import os

admin_videos_bp = Blueprint('admin_videos', __name__, url_prefix='/admin')

def require_admin():
	is_admin = (
		session.get("admin") == True or
		session.get("admin_logged_in") == True or
		session.get("user_type") == "admin"
	)
	if not is_admin:
		abort(403)

@admin_videos_bp.route('/videos', methods=['GET'])
def manage_videos():
    """Local-only video admin page."""
    require_admin()
    featured = Product.query.filter(
        Product.featured == True,
        Product.video_key.isnot(None)
    ).order_by(Product.created_at.desc()).all()
    candidates = Product.query.filter(
        Product.featured == False,
        Product.video_key.isnot(None)
    ).order_by(Product.created_at.desc()).all()
    return render_template('admin_homepage_videos.html', featured=featured, candidates=candidates)

@admin_videos_bp.route('/homepage-videos', methods=['GET'])
def legacy_homepage_videos():
    return redirect(url_for('admin_videos.manage_videos'))

@admin_videos_bp.route('/videos/feature/<int:product_id>', methods=['POST'])
def feature_video(product_id):
	require_admin()
	product = Product.query.get_or_404(product_id)
	product.featured = True
	db.session.commit()
	flash(f'"{product.title}" featured.', 'success')
	return redirect(url_for('admin_videos.manage_videos'))

@admin_videos_bp.route('/videos/unfeature/<int:product_id>', methods=['POST'])
def unfeature_video(product_id):
	require_admin()
	product = Product.query.get_or_404(product_id)
	product.featured = False
	db.session.commit()
	flash(f'"{product.title}" unfeatured.', 'info')
	return redirect(url_for('admin_videos.manage_videos'))

@admin_videos_bp.route('/videos/new', methods=['GET', 'POST'])
def new_video():
    """Create a new local video product."""
    require_admin()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip() or None
        price_cents = request.form.get('price_cents', type=int) or 0
        video_file = request.files.get('video_file')
        thumb_file = request.files.get('thumbnail')

        errors = []
        if not title:
            errors.append('Title is required.')
        if not video_file or video_file.filename == '':
            errors.append('Video file is required.')
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admin_new_video.html')

        storage_backend = current_app.extensions.get('active_storage')
        saved_video_key = None
        try:
            ok, result = storage_backend.upload_file(file=video_file, folder='') if hasattr(storage_backend, 'upload_file') else (False, {'error': 'Storage backend not available'})
            if not ok:
                flash(f"Upload failed: {result.get('error')}", 'error')
                return render_template('admin_new_video.html')
            saved_video_key = result.get('stored_name') or result.get('filename') or result.get('blob_name') or result.get('id')
        except Exception as e:
            flash(f'Unexpected upload error: {e}', 'error')
            return render_template('admin_new_video.html')

        thumb_key = None
        if thumb_file and thumb_file.filename:
            try:
                uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(uploads_dir, exist_ok=True)
                secure_name = secure_filename(thumb_file.filename)
                thumb_file.save(os.path.join(uploads_dir, secure_name))
                thumb_key = secure_name
            except Exception as e:
                flash(f'Thumbnail save failed: {e}', 'warning')

        product = Product(
            title=title,
            description=description,
            price_cents=price_cents,
            media_key=thumb_key or saved_video_key,
            video_key=saved_video_key,
            video_thumbnail=thumb_key,
            video_duration=None,
            category=category,
            stock=1,
            video_hosting_type='local'
        )
        try:
            db.session.add(product)
            db.session.commit()
            if request.form.get('feature') == 'on':
                product.featured = True
                db.session.commit()
            flash('Video created successfully.', 'success')
            return redirect(url_for('admin_videos.manage_videos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create product: {e}', 'error')
            return render_template('admin_new_video.html')

    return render_template('admin_new_video.html')

@admin_videos_bp.route('/videos/update/<int:product_id>', methods=['POST'])
def update_homepage_video(product_id):
    """Update metadata for a local featured video."""
    require_admin()
    product = Product.query.get_or_404(product_id)
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    client_name = request.form.get('client_name', '').strip()
    client_testimonial = request.form.get('client_testimonial', '').strip()
    price_cents = request.form.get('price_cents', type=int)

    if not title:
        flash('Title is required.', 'error')
        return redirect(url_for('admin_videos.manage_videos'))

    product.title = title
    if description:
        product.description = description
    if category:
        product.category = category
    if client_name:
        product.client_name = client_name
    if client_testimonial:
        product.client_testimonial = client_testimonial
    if price_cents is not None:
        product.price_cents = price_cents

    thumb_file = request.files.get('thumbnail')
    if thumb_file and thumb_file.filename:
        try:
            uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            secure_name = secure_filename(thumb_file.filename)
            thumb_file.save(os.path.join(uploads_dir, secure_name))
            product.video_thumbnail = secure_name
            if not product.media_key:
                product.media_key = secure_name
        except Exception as e:
            flash(f'Thumbnail update failed: {e}', 'warning')

    try:
        db.session.commit()
        flash('Video updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Update failed: {e}', 'error')
    return redirect(url_for('admin_videos.manage_videos'))

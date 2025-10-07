from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, session
from models import Product, db
from flask import current_app
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

@admin_videos_bp.route('/homepage-videos', methods=['GET'])
def manage_homepage_videos():
	require_admin()
	# Featured products with video content (local or drive)
	featured = Product.query.filter(Product.featured == True).order_by(Product.created_at.desc()).all()
	# Candidates: video products not yet featured
	candidates = Product.query.filter(
		Product.featured == False,
		(Product.video_key.isnot(None)) | (Product.google_drive_video_id.isnot(None))
	).order_by(Product.created_at.desc()).all()
	return render_template('admin_homepage_videos.html', featured=featured, candidates=candidates)

@admin_videos_bp.route('/homepage-videos/feature/<int:product_id>', methods=['POST'])
def feature_video(product_id):
	require_admin()
	product = Product.query.get_or_404(product_id)
	product.featured = True
	db.session.commit()
	flash(f'"{product.title}" added to homepage videos.', 'success')
	return redirect(url_for('admin_videos.manage_homepage_videos'))

@admin_videos_bp.route('/homepage-videos/unfeature/<int:product_id>', methods=['POST'])
def unfeature_video(product_id):
	require_admin()
	product = Product.query.get_or_404(product_id)
	product.featured = False
	db.session.commit()
	flash(f'"{product.title}" removed from homepage videos.', 'info')
	return redirect(url_for('admin_videos.manage_homepage_videos'))

@admin_videos_bp.route('/videos/new', methods=['GET', 'POST'])
def new_video():
	"""Create a new video product (basic metadata + file upload)."""
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

		# Save video file to local storage (respect active backend if later extended)
		storage_backend = current_app.extensions.get('active_storage')
		saved_video_key = None
		public_url = None
		try:
			# Use the storage service abstraction if it supports upload_file signature
			ok, result = storage_backend.upload_file(file=video_file, folder='') if hasattr(storage_backend, 'upload_file') else (False, {'error': 'Storage backend not available'})
			if not ok:
				flash(f"Upload failed: {result.get('error')}", 'error')
				return render_template('admin_new_video.html')
			# Normalize keys
			saved_video_key = result.get('stored_name') or result.get('filename') or result.get('blob_name') or result.get('id')
			public_url = result.get('public_url') or result.get('url')
		except Exception as e:
			flash(f'Unexpected upload error: {e}', 'error')
			return render_template('admin_new_video.html')

		# Handle optional thumbnail - store in same uploads directory if provided
		thumb_key = None
		if thumb_file and thumb_file.filename:
			try:
				# For simplicity, store thumbnail directly in static/uploads
				uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
				os.makedirs(uploads_dir, exist_ok=True)
				secure_name = secure_filename(thumb_file.filename)
				thumb_path = os.path.join(uploads_dir, secure_name)
				thumb_file.save(thumb_path)
				thumb_key = secure_name
			except Exception as e:
				flash(f'Thumbnail save failed: {e}', 'warning')

		# Create product record
		product = Product(
			title=title,
			description=description,
			price_cents=price_cents,
			media_key=thumb_key or saved_video_key,  # media_key used for listing image
			video_key=saved_video_key,
			video_thumbnail=thumb_key,
			video_duration=None,  # Could be populated later with analysis
			category=category,
			stock=1,
			video_hosting_type='local'
		)
		try:
			db.session.add(product)
			db.session.commit()
			flash('Video created successfully.', 'success')
			# Optionally feature immediately if checkbox selected
			if request.form.get('feature') == 'on':
				product.featured = True
				db.session.commit()
			return redirect(url_for('admin_videos.manage_homepage_videos'))
		except Exception as e:
			db.session.rollback()
			flash(f'Failed to create product: {e}', 'error')
			return render_template('admin_new_video.html')

	return render_template('admin_new_video.html')

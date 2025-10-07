from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, session
from models import Product, db

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

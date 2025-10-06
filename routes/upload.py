"""
Enhanced file upload routes for FlashStudio
Integrates with Google Drive service for robust file management
"""
import os
import logging
from flask import Blueprint, request, jsonify, abort, current_app
from utils.google_drive import drive_storage_service as blob_storage_service

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload_bp", __name__, url_prefix='/api')

@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    """Upload a file to Google Drive Storage"""
    try:
        # Check if file is in request
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Get optional parameters
        folder = request.form.get("folder", "")
        custom_name = request.form.get("custom_name")

        # Upload file using enhanced storage service
        success, result = blob_storage_service.upload_file(
            file=file,
            folder=folder,
            custom_name=custom_name
        )

        if success:
            logger.info(f"File uploaded successfully: {result['filename']}")
            return jsonify(result), 200
        else:
            logger.error(f"File upload failed: {result['error']}")
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Unexpected error in upload: {e}")
        return jsonify({"error": "Upload failed"}), 500

@upload_bp.route("/files", methods=["GET"])
def list_files():
    """List uploaded files"""
    try:
        folder = request.args.get("folder", "")
        limit = int(request.args.get("limit", 100))

        success, result = blob_storage_service.list_files(folder=folder, limit=limit)

        if success:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({"error": "Failed to list files"}), 500

@upload_bp.route("/files/<path:blob_name>", methods=["DELETE"])
def delete_file(blob_name):
    """Delete a file from storage"""
    try:
        success, result = blob_storage_service.delete_file(blob_name)

        if success:
            logger.info(f"File deleted successfully: {blob_name}")
            return jsonify(result), 200
        else:
            logger.error(f"File deletion failed: {result['error']}")
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error deleting file {blob_name}: {e}")
        return jsonify({"error": "Delete failed"}), 500

@upload_bp.route("/files/<path:blob_name>/info", methods=["GET"])
def get_file_info(blob_name):
    """Get file information"""
    try:
        success, result = blob_storage_service.get_file_info(blob_name)

        if success:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error getting file info for {blob_name}: {e}")
        return jsonify({"error": "Failed to get file info"}), 500

@upload_bp.route("/files/<path:blob_name>/download-url", methods=["GET"])
def generate_download_url(blob_name):
    """Generate a secure download URL"""
    try:
        expiry_hours = int(request.args.get("expiry_hours", 24))
        
        download_url = blob_storage_service.generate_download_url(
            file_id=blob_name,
            expiry_hours=expiry_hours
        )

        if download_url:
            return jsonify({
                "download_url": download_url,
                "expires_in_hours": expiry_hours
            }), 200
        else:
            return jsonify({"error": "Failed to generate download URL"}), 400

    except Exception as e:
        logger.error(f"Error generating download URL for {blob_name}: {e}")
        return jsonify({"error": "Failed to generate download URL"}), 500

# Legacy route for backward compatibility
@upload_bp.route("/upload-legacy", methods=["POST"])
def upload_file_legacy():
    """Legacy upload endpoint for backward compatibility"""
    try:
        if "file" not in request.files:
            abort(400, "No file field named 'file'")

        file = request.files["file"]
        if file.filename == "":
            abort(400, "No selected file")

        success, result = blob_storage_service.upload_file(file=file)

        if success:
            # Return in legacy format
            return jsonify({
                "url": result["public_url"],
                "blob": result["blob_name"]
            })
        else:
            abort(400, result["error"])

    except Exception as e:
        logger.error(f"Legacy upload error: {e}")
        abort(500, "Upload failed")

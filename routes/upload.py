"""
Enhanced file upload routes for FlashStudio
Local storage implementation for file management
"""
import os
import logging
from flask import Blueprint, request, jsonify, abort, current_app
from utils.local_storage import local_storage_service

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload_bp", __name__, url_prefix='/api')

def get_storage():
    """Return local storage service"""
    return local_storage_service

@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    """Upload a file to local storage"""
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
        storage = get_storage()
        success, result = storage.upload_file(
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
        storage = get_storage()
        success, result = storage.list_files(folder=folder, limit=limit)
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
        storage = get_storage()
        # local storage delete uses simple id; drive service expects blob/file id
        success, result = storage.delete_file(blob_name)
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
        storage = get_storage()
        # local storage lacks get_file_info; emulate minimal response
        if hasattr(storage, 'get_file_info'):
            success, result = storage.get_file_info(blob_name)
        else:
            # fabricate info
            public_url = f"/media/{blob_name}"
            result = {'id': blob_name, 'public_url': public_url}
            success = True

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
        
        storage = get_storage()
        if hasattr(storage, 'generate_download_url'):
            download_url = storage.generate_download_url(
            file_id=blob_name,
            expiry_hours=expiry_hours
            )
        else:
            # Local storage: just return direct URL (not expiring)
            download_url = f"/media/{blob_name}"

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
        storage = get_storage()
        success, result = storage.upload_file(file=file)

        if success:
            # Return in legacy format (normalize keys if missing)
            public_url = result.get("public_url") or result.get("url")
            blob_name = result.get("blob_name") or result.get("id") or result.get("stored_name")
            return jsonify({
                "url": public_url,
                "blob": blob_name
            })
        else:
            abort(400, result.get("error", "upload failed"))

    except Exception as e:
        logger.error(f"Legacy upload error: {e}")
        abort(500, "Upload failed")

"""
Enhanced Upload Routes with Google Drive Integration for FlashStudio
Provides dual storage options: Google Drive (primary) + Azure Blob (backup)
"""
import os
import logging
from flask import Blueprint, request, jsonify, abort, current_app
from utils.google_drive import drive_storage_service
import requests

logger = logging.getLogger(__name__)

# Enhanced upload blueprint
enhanced_upload_bp = Blueprint("enhanced_upload_bp", __name__, url_prefix='/api/v2')

@enhanced_upload_bp.route("/upload", methods=["POST"])
def upload_file_enhanced():
    """
    Enhanced upload with Google Drive + Azure Blob dual storage
    
    Features:
    - Primary upload to Google Drive
    - Backup upload to Azure Blob Storage  
    - Automatic image processing trigger
    - Metadata tracking in database
    """
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
        enable_processing = request.form.get("enable_processing", "true").lower() == "true"
        storage_preference = request.form.get("storage", "google_drive")  # google_drive, azure, both

        results = {"primary_storage": None, "backup_storage": None, "processing": None}
        
        # Upload to Google Drive (Primary)
        if storage_preference in ["google_drive", "both"]:
            google_success, google_result = drive_storage_service.upload_file(
                file=file,
                folder=folder,
                custom_name=custom_name
            )
            
            results["primary_storage"] = {
                "service": "google_drive",
                "success": google_success,
                "data": google_result
            }
            
            # Reset file stream for potential second upload
            file.stream.seek(0)

        # Upload to Azure Blob (Secondary/Backup)
        if storage_preference in ["azure", "both"]:
            azure_success, azure_result = upload_to_azure_blob_backup(file, folder, custom_name)
            
            results["backup_storage"] = {
                "service": "azure_blob",
                "success": azure_success,
                "data": azure_result
            }

        # Trigger automatic image processing if enabled
        if enable_processing and file.content_type and file.content_type.startswith('image/'):
            processing_result = trigger_image_processing(
                file_info=results["primary_storage"]["data"] if results["primary_storage"] and results["primary_storage"]["success"] else results["backup_storage"]["data"],
                original_filename=file.filename
            )
            results["processing"] = processing_result

        # Save metadata to database
        save_upload_metadata(results, file.filename, folder)

        # Determine response based on success
        primary_success = results["primary_storage"] and results["primary_storage"]["success"]
        backup_success = results["backup_storage"] and results["backup_storage"]["success"]
        
        if primary_success or backup_success:
            logger.info(f"File uploaded successfully: {file.filename}")
            return jsonify({
                "success": True,
                "message": "File uploaded successfully",
                "results": results,
                "primary_url": results["primary_storage"]["data"].get("public_url") if primary_success else None,
                "backup_url": results["backup_storage"]["data"].get("public_url") if backup_success else None
            }), 200
        else:
            logger.error(f"All upload methods failed for: {file.filename}")
            return jsonify({
                "success": False,
                "error": "All upload methods failed",
                "results": results
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in enhanced upload: {e}")
        return jsonify({"error": "Upload failed", "details": str(e)}), 500


@enhanced_upload_bp.route("/upload-to-drive", methods=["POST"])
def upload_to_google_drive_only():
    """Upload directly to Google Drive only"""
    
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        folder = request.form.get("folder", "")
        custom_name = request.form.get("custom_name")

        success, result = drive_storage_service.upload_file(
            file=file,
            folder=folder,
            custom_name=custom_name
        )

        if success:
            # Trigger processing if it's an image
            if file.content_type and file.content_type.startswith('image/'):
                trigger_image_processing(result, file.filename)
            
            return jsonify({
                "success": True,
                "message": "File uploaded to Google Drive",
                **result
            }), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Google Drive upload error: {e}")
        return jsonify({"error": "Google Drive upload failed"}), 500


@enhanced_upload_bp.route("/migrate-to-drive", methods=["POST"])
def migrate_azure_to_google_drive():
    """
    Migrate existing files from Azure Blob Storage to Google Drive
    
    Body: {
        "blob_names": ["file1.jpg", "file2.png"],
        "target_folder": "migrated_files"
    }
    """
    
    try:
        data = request.get_json()
        if not data or "blob_names" not in data:
            return jsonify({"error": "blob_names required"}), 400

        blob_names = data["blob_names"]
        target_folder = data.get("target_folder", "migrated")
        
        migration_results = []
        
        for blob_name in blob_names:
            try:
                # Download from Azure Blob
                file_content = download_from_azure_blob(blob_name)
                if not file_content:
                    migration_results.append({
                        "blob_name": blob_name,
                        "success": False,
                        "error": "Failed to download from Azure"
                    })
                    continue
                
                # Upload to Google Drive
                drive_result = upload_content_to_drive(file_content, blob_name, target_folder)
                migration_results.append({
                    "blob_name": blob_name,
                    "success": drive_result["success"],
                    "google_drive_id": drive_result.get("file_id"),
                    "error": drive_result.get("error")
                })
                
            except Exception as e:
                migration_results.append({
                    "blob_name": blob_name,
                    "success": False,
                    "error": str(e)
                })
        
        successful_migrations = sum(1 for result in migration_results if result["success"])
        
        return jsonify({
            "total_files": len(blob_names),
            "successful_migrations": successful_migrations,
            "failed_migrations": len(blob_names) - successful_migrations,
            "results": migration_results
        }), 200

    except Exception as e:
        logger.error(f"Migration error: {e}")
        return jsonify({"error": "Migration failed"}), 500


def upload_to_azure_blob_backup(file, folder="", custom_name=None):
    """Upload file to Azure Blob Storage as backup"""
    
    try:
        # This would use your existing Azure Blob Storage service
        # You can implement this based on your current Azure setup
        
        from azure.storage.blob import BlobServiceClient
        
        connection_string = current_app.config.get('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            return False, {"error": "Azure Blob Storage not configured"}
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "uploads"
        
        # Generate blob name
        import uuid
        from datetime import datetime
        from werkzeug.utils import secure_filename
        
        if custom_name:
            filename = secure_filename(custom_name)
        else:
            filename = secure_filename(file.filename)
        
        # Add folder prefix
        if folder:
            blob_name = f"{folder}/{filename}"
        else:
            blob_name = filename
        
        # Upload
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        blob_client.upload_blob(
            file.stream.read(),
            blob_type="BlockBlob",
            overwrite=True
        )
        
        # Generate URL
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        
        return True, {
            "blob_name": blob_name,
            "public_url": blob_url,
            "container": container_name
        }
        
    except Exception as e:
        logger.error(f"Azure Blob backup upload failed: {e}")
        return False, {"error": str(e)}


def trigger_image_processing(file_info, original_filename):
    """Trigger Azure Functions image processing"""
    
    try:
        # Call Azure Functions ImageProcessor via HTTP
        function_url = current_app.config.get('AZURE_FUNCTIONS_URL')
        if not function_url:
            return {"success": False, "error": "Azure Functions URL not configured"}
        
        processing_endpoint = f"{function_url}/api/ProcessImageManual"
        
        payload = {
            "file_info": file_info,
            "original_filename": original_filename,
            "processing_options": {
                "sizes": ["thumbnail", "medium", "large"],
                "formats": ["jpeg", "webp"],
                "quality": 85
            }
        }
        
        response = requests.post(
            processing_endpoint,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True, "processing_id": response.json().get("processing_id")}
        else:
            return {"success": False, "error": f"Processing failed: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Failed to trigger image processing: {e}")
        return {"success": False, "error": str(e)}


def save_upload_metadata(results, filename, folder):
    """Save upload metadata to database"""
    
    try:
        # This would save to your existing database
        # You can implement this based on your database models
        
        from models import FileUpload, db  # Adjust based on your models
        from datetime import datetime
        
        upload_record = FileUpload(
            filename=filename,
            folder=folder,
            google_drive_id=results.get("primary_storage", {}).get("data", {}).get("file_id"),
            azure_blob_name=results.get("backup_storage", {}).get("data", {}).get("blob_name"),
            upload_date=datetime.utcnow(),
            processing_status="pending" if results.get("processing") else "none"
        )
        
        db.session.add(upload_record)
        db.session.commit()
        
        logger.info(f"Upload metadata saved for: {filename}")
        
    except Exception as e:
        logger.error(f"Failed to save upload metadata: {e}")


def download_from_azure_blob(blob_name):
    """Download file content from Azure Blob Storage"""
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        connection_string = current_app.config.get('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            return None
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(
            container="uploads",
            blob=blob_name
        )
        
        return blob_client.download_blob().readall()
        
    except Exception as e:
        logger.error(f"Failed to download from Azure Blob: {e}")
        return None


def upload_content_to_drive(file_content, filename, folder=""):
    """Upload file content to Google Drive"""
    
    try:
        import io
        from werkzeug.datastructures import FileStorage
        
        # Create a file-like object from content
        file_stream = io.BytesIO(file_content)
        file_obj = FileStorage(
            stream=file_stream,
            filename=filename,
            content_type="application/octet-stream"
        )
        
        success, result = drive_storage_service.upload_file(
            file=file_obj,
            folder=folder
        )
        
        return {
            "success": success,
            "file_id": result.get("file_id") if success else None,
            "error": result.get("error") if not success else None
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# Register the enhanced blueprint in your main app
# Add this to your main Flask app file:
# from routes.enhanced_upload import enhanced_upload_bp
# app.register_blueprint(enhanced_upload_bp)
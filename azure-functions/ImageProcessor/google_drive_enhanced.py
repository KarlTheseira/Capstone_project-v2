import azure.functions as func
import logging
from PIL import Image, ImageOps
import io
import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

def main(myblob: func.InputStream) -> None:
    """
    Enhanced Image Processor with Google Drive Integration
    
    This function can process images from both Azure Blob Storage and Google Drive:
    - Creates optimized versions (thumbnail, medium, large)
    - Uploads processed images to Google Drive
    - Maintains Azure Blob Storage compatibility
    """
    
    logging.info(f'🖼️  Processing image: {myblob.name}')
    
    try:
        # Read the uploaded image
        image_data = myblob.read()
        
        # Check if it's actually an image
        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception:
            logging.warning(f"⚠️  File {myblob.name} is not a valid image, skipping")
            return
        
        # Fix image orientation (from EXIF data)
        image = ImageOps.exif_transpose(image)
        
        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Get filename without path
        filename = myblob.name.split('/')[-1]
        name_without_ext, ext = os.path.splitext(filename)
        
        # Process images in multiple sizes
        sizes = {
            'thumbnail': (300, 300),
            'medium': (800, 800),
            'large': (1200, 1200)
        }
        
        processed_files = []
        
        for size_name, (width, height) in sizes.items():
            # Create resized image
            resized_image = create_optimized_image(image, width, height)
            
            # Convert to bytes
            output_buffer = io.BytesIO()
            format_type = 'JPEG' if ext.lower() in ['.jpg', '.jpeg'] else 'PNG'
            quality = 85 if format_type == 'JPEG' else None
            
            if quality:
                resized_image.save(output_buffer, format=format_type, quality=quality, optimize=True)
            else:
                resized_image.save(output_buffer, format=format_type, optimize=True)
            
            processed_image_data = output_buffer.getvalue()
            
            # Generate new filename
            processed_filename = f"{name_without_ext}_{size_name}{ext}"
            
            # Upload to Google Drive (NEW FUNCTIONALITY)
            drive_file_id = upload_to_google_drive(processed_image_data, processed_filename)
            
            # Also upload to Azure Blob Storage (for backward compatibility)
            azure_success = upload_to_azure_blob(processed_image_data, processed_filename)
            
            processed_files.append({
                'size': size_name,
                'filename': processed_filename,
                'google_drive_id': drive_file_id,
                'azure_uploaded': azure_success,
                'dimensions': f"{width}x{height}"
            })
            
            logging.info(f"✅ Created {size_name} version: {processed_filename}")
        
        logging.info(f"🎉 Successfully processed {filename} in {len(processed_files)} sizes")
        
        # Update database with new file references (optional)
        update_database_references(filename, processed_files)
        
    except Exception as e:
        logging.error(f"💥 Error processing image {myblob.name}: {str(e)}")


def upload_to_google_drive(image_data: bytes, filename: str) -> str:
    """Upload processed image to Google Drive"""
    
    try:
        # Get Google Drive configuration from environment
        credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_JSON')
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        
        if not credentials_json or not folder_id:
            logging.warning("Google Drive not configured, skipping upload")
            return None
        
        # Parse credentials
        creds_data = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        # Build Drive service
        service = build('drive', 'v3', credentials=credentials)
        
        # Create file metadata
        file_metadata = {
            'name': f"processed_{filename}",
            'parents': [folder_id],
            'description': f"Auto-processed by FlashStudio ImageProcessor on {myblob.name}"
        }
        
        # Determine MIME type
        mime_type = 'image/jpeg' if filename.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
        
        # Create media upload
        media = MediaIoBaseUpload(
            io.BytesIO(image_data),
            mimetype=mime_type,
            resumable=True
        )
        
        # Upload file
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name'
        ).execute()
        
        logging.info(f"📁 Uploaded to Google Drive: {uploaded_file['name']} (ID: {uploaded_file['id']})")
        return uploaded_file['id']
        
    except Exception as e:
        logging.error(f"❌ Google Drive upload failed: {e}")
        return None


def upload_to_azure_blob(image_data: bytes, filename: str) -> bool:
    """Upload to Azure Blob Storage (existing functionality)"""
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            logging.warning("Azure Blob Storage not configured")
            return False
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "processed-images"
        
        # Upload to Azure
        blob_client = blob_service_client.get_blob_client(
            container=container_name, 
            blob=filename
        )
        
        blob_client.upload_blob(
            image_data, 
            blob_type="BlockBlob",
            overwrite=True
        )
        
        logging.info(f"📦 Uploaded to Azure Blob: {filename}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Azure Blob upload failed: {e}")
        return False


def create_optimized_image(image: Image.Image, width: int, height: int) -> Image.Image:
    """Create optimized resized image"""
    
    # Calculate the best fit size maintaining aspect ratio
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    
    # Create a new image with the exact target size and paste the resized image
    if image.size != (width, height):
        # Create background (white for JPEG, transparent for PNG)
        if image.mode == 'RGBA':
            background = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        else:
            background = Image.new('RGB', (width, height), (255, 255, 255))
        
        # Calculate position to center the image
        x = (width - image.size[0]) // 2
        y = (height - image.size[1]) // 2
        
        background.paste(image, (x, y))
        return background
    
    return image


def update_database_references(original_filename: str, processed_files: list):
    """Update database with processed file references"""
    
    try:
        # This would connect to your Flask app's database
        # You can implement this based on your database structure
        
        flask_app_url = os.environ.get('FLASK_APP_URL')
        api_key = os.environ.get('ANALYTICS_API_KEY')
        
        if flask_app_url and api_key:
            import requests
            
            payload = {
                'original_file': original_filename,
                'processed_files': processed_files,
                'processor': 'azure_functions_imageprocessor'
            }
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'{flask_app_url}/api/update-processed-images',
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logging.info("✅ Database updated with processed file references")
            else:
                logging.warning(f"⚠️  Failed to update database: {response.status_code}")
        
    except Exception as e:
        logging.error(f"❌ Failed to update database references: {e}")
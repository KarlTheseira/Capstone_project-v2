import azure.functions as func
import logging
from PIL import Image, ImageOps
import io
import os
from azure.storage.blob import BlobServiceClient

def main(myblob: func.InputStream) -> None:
    """
    Azure Function to automatically process uploaded images
    
    This function triggers when an image is uploaded to the 'uploads' container
    and creates optimized versions:
    - Thumbnail (300x300)
    - Medium size (800x800) 
    - Optimized original
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
        
        # Setup blob service client
        connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            logging.error("❌ AZURE_STORAGE_CONNECTION_STRING not configured")
            return
            
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Create different sizes
        sizes = [
            {
                'name': 'thumbnail',
                'size': (300, 300),
                'suffix': '_thumb',
                'quality': 85,
                'container': 'thumbnails'
            },
            {
                'name': 'medium',
                'size': (800, 800),
                'suffix': '_medium',
                'quality': 90,
                'container': 'processed'
            },
            {
                'name': 'optimized',
                'size': None,  # Keep original size
                'suffix': '_optimized',
                'quality': 95,
                'container': 'processed'
            }
        ]
        
        for size_config in sizes:
            try:
                processed_image = create_processed_image(
                    image, 
                    size_config['size'], 
                    size_config['quality']
                )
                
                # Generate filename
                processed_filename = f"{name_without_ext}{size_config['suffix']}.jpg"
                
                # Upload to blob storage
                upload_processed_image(
                    blob_service_client,
                    processed_image,
                    size_config['container'],
                    processed_filename
                )
                
                logging.info(f"✅ Created {size_config['name']}: {processed_filename}")
                
            except Exception as e:
                logging.error(f"❌ Failed to create {size_config['name']}: {e}")
        
        logging.info(f"🎉 Image processing completed for: {filename}")
        
    except Exception as e:
        logging.error(f"💥 Error processing image {myblob.name}: {str(e)}")


def create_processed_image(image, target_size, quality):
    """Create a processed version of the image"""
    
    processed = image.copy()
    
    if target_size:
        # Resize while maintaining aspect ratio
        processed.thumbnail(target_size, Image.Resampling.LANCZOS)
    
    # Save to bytes buffer
    img_buffer = io.BytesIO()
    processed.save(
        img_buffer, 
        format='JPEG',
        quality=quality,
        optimize=True,
        progressive=True
    )
    img_buffer.seek(0)
    
    return img_buffer


def upload_processed_image(blob_service_client, image_buffer, container_name, filename):
    """Upload processed image to blob storage"""
    
    try:
        # Create container if it doesn't exist
        try:
            container_client = blob_service_client.get_container_client(container_name)
            container_client.get_container_properties()
        except Exception:
            # Container doesn't exist, create it
            blob_service_client.create_container(
                container_name,
                public_access='blob'  # Allow public read access
            )
            logging.info(f"📁 Created container: {container_name}")
        
        # Upload the image
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=filename
        )
        
        blob_client.upload_blob(
            image_buffer.getvalue(),
            overwrite=True,
            content_type='image/jpeg'
        )
        
        # Log the public URL
        blob_url = blob_client.url
        logging.info(f"📍 Uploaded to: {blob_url}")
        
    except Exception as e:
        logging.error(f"💥 Failed to upload {filename} to {container_name}: {e}")
        raise


# Helper function to get image metadata (optional, for analytics)
def get_image_metadata(image):
    """Extract useful metadata from image"""
    
    metadata = {
        'format': image.format,
        'mode': image.mode,
        'size': image.size,
        'width': image.width,
        'height': image.height
    }
    
    # Get EXIF data if available
    if hasattr(image, '_getexif') and image._getexif():
        exif_data = image._getexif()
        if exif_data:
            # Extract common EXIF tags
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if tag in ['DateTime', 'Make', 'Model', 'Software']:
                    metadata[f'exif_{tag}'] = value
    
    return metadata
"""
Google Drive Storage Service for FlashStudio
Provides robust file management, error handling, and production features
Replaces Azure Blob Storage with Google Drive integration
"""
import os
import uuid
import json
import logging
import io
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timedelta
from flask import current_app
from werkzeug.utils import secure_filename

# Google Drive imports
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

logger = logging.getLogger(__name__)

class GoogleDriveService:
    """Enhanced Google Drive storage service with error handling and features"""
    
    def __init__(self):
        self.service = None
        self.folder_id = None
        self._initialized = False
        self._credentials = None
    
    def init_app(self, app):
        """Initialize with Flask app configuration"""
        try:
            # Check for Google Drive configuration
            credentials_json = app.config.get('GOOGLE_DRIVE_CREDENTIALS_JSON')
            folder_id = app.config.get('GOOGLE_DRIVE_FOLDER_ID')
            
            if not credentials_json or not folder_id:
                logger.warning("Google Drive not configured - missing credentials or folder ID")
                self._initialized = False
                return
            
            # Initialize credentials
            if isinstance(credentials_json, str):
                # If it's a JSON string, parse it
                try:
                    creds_data = json.loads(credentials_json)
                except json.JSONDecodeError:
                    # If it's a file path, read the file
                    with open(credentials_json, 'r') as f:
                        creds_data = json.load(f)
            else:
                creds_data = credentials_json
            
            # Create credentials from service account info
            from google.oauth2 import service_account
            self._credentials = service_account.Credentials.from_service_account_info(
                creds_data,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            
            # Build the Drive API service
            self.service = build('drive', 'v3', credentials=self._credentials)
            self.folder_id = folder_id
            
            # Verify folder exists and is accessible
            self._verify_folder_access()
            
            self._initialized = True
            logger.info("Google Drive service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            self._initialized = False
    
    def is_configured(self) -> bool:
        """Check if Google Drive storage is properly configured"""
        return self._initialized and self.service is not None
    
    def _verify_folder_access(self):
        """Verify the specified folder exists and is accessible"""
        try:
            folder = self.service.files().get(fileId=self.folder_id).execute()
            logger.info(f"Connected to Google Drive folder: {folder.get('name', 'Unknown')}")
        except HttpError as e:
            logger.error(f"Cannot access Google Drive folder {self.folder_id}: {e}")
            raise
    
    def upload_file(self, file, folder: str = "", custom_name: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Upload a file to Google Drive
        
        Args:
            file: File object from request.files
            folder: Optional subfolder path (simulated with naming)
            custom_name: Optional custom filename
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        if not self.is_configured():
            return False, {"error": "Google Drive not configured"}
        
        try:
            # Validate file
            if not file or file.filename == "":
                return False, {"error": "No file provided"}
            
            if not self._is_allowed_file(file.filename):
                return False, {"error": "File type not allowed"}
            
            # Generate file name
            drive_filename = self._generate_file_name(file.filename, folder, custom_name)
            
            # Get MIME type
            mime_type = file.mimetype or 'application/octet-stream'
            
            # Create file metadata
            file_metadata = {
                'name': drive_filename,
                'parents': [self.folder_id],
                'description': f"Uploaded by FlashStudio on {datetime.utcnow().isoformat()}"
            }
            
            # Read file content
            file_content = file.stream.read()
            file.stream.seek(0)  # Reset stream position
            
            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            uploaded_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,mimeType,webViewLink,webContentLink'
            ).execute()
            
            # Make file publicly viewable (optional)
            try:
                self.service.permissions().create(
                    fileId=uploaded_file['id'],
                    body={
                        'role': 'reader',
                        'type': 'anyone'
                    }
                ).execute()
            except HttpError as e:
                logger.warning(f"Could not make file public: {e}")
            
            logger.info(f"File uploaded successfully: {drive_filename} (ID: {uploaded_file['id']})")
            
            # Generate public URL
            public_url = f"https://drive.google.com/uc?id={uploaded_file['id']}&export=download"
            
            return True, {
                "file_id": uploaded_file['id'],
                "filename": drive_filename,
                "public_url": public_url,
                "view_url": uploaded_file.get('webViewLink', ''),
                "size": uploaded_file.get('size', len(file_content)),
                "content_type": mime_type,
                "folder": folder
            }
            
        except HttpError as e:
            logger.error(f"Google Drive HTTP error uploading file: {e}")
            return False, {"error": f"Drive API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return False, {"error": "Upload failed"}
    
    def delete_file(self, file_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete a file from Google Drive
        
        Args:
            file_id: Google Drive file ID to delete
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        if not self.is_configured():
            return False, {"error": "Google Drive not configured"}
        
        try:
            # Get file info first for logging
            try:
                file_info = self.service.files().get(fileId=file_id, fields='name').execute()
                filename = file_info.get('name', 'Unknown')
            except:
                filename = 'Unknown'
            
            # Delete the file
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"File deleted successfully: {filename} (ID: {file_id})")
            
            return True, {"message": f"File {filename} deleted successfully"}
            
        except HttpError as e:
            logger.error(f"Google Drive HTTP error deleting file {file_id}: {e}")
            return False, {"error": f"Drive API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error deleting file {file_id}: {e}")
            return False, {"error": "Delete failed"}
    
    def generate_download_url(self, file_id: str, expiry_hours: int = 24) -> Optional[str]:
        """
        Generate a direct download URL for a file
        
        Args:
            file_id: Google Drive file ID
            expiry_hours: Not used for Google Drive (URLs don't expire)
            
        Returns:
            Direct download URL or None if failed
        """
        if not self.is_configured():
            return None
        
        try:
            # For Google Drive, we can use the direct download URL
            return f"https://drive.google.com/uc?id={file_id}&export=download"
            
        except Exception as e:
            logger.error(f"Error generating download URL for {file_id}: {e}")
            return None
    
    def list_files(self, folder: str = "", limit: int = 100) -> Tuple[bool, Dict[str, Any]]:
        """
        List files in the Google Drive folder
        
        Args:
            folder: Optional folder prefix to filter by
            limit: Maximum number of files to return
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        if not self.is_configured():
            return False, {"error": "Google Drive not configured"}
        
        try:
            # Build query
            query = f"'{self.folder_id}' in parents and trashed=false"
            if folder:
                query += f" and name contains '{folder}'"
            
            # List files
            results = self.service.files().list(
                q=query,
                pageSize=min(limit, 1000),
                fields="files(id,name,size,mimeType,modifiedTime,webViewLink,webContentLink)"
            ).execute()
            
            files = []
            for file_item in results.get('files', []):
                files.append({
                    "id": file_item['id'],
                    "name": file_item['name'],
                    "size": int(file_item.get('size', 0)) if file_item.get('size') else None,
                    "last_modified": file_item.get('modifiedTime'),
                    "content_type": file_item.get('mimeType'),
                    "url": f"https://drive.google.com/uc?id={file_item['id']}&export=download",
                    "view_url": file_item.get('webViewLink', '')
                })
            
            return True, {
                "files": files,
                "total": len(files),
                "folder": self.folder_id
            }
            
        except HttpError as e:
            logger.error(f"Google Drive HTTP error listing files: {e}")
            return False, {"error": f"Drive API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error listing files: {e}")
            return False, {"error": "List operation failed"}
    
    def get_file_info(self, file_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get information about a specific file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        if not self.is_configured():
            return False, {"error": "Google Drive not configured"}
        
        try:
            file_info = self.service.files().get(
                fileId=file_id,
                fields="id,name,size,mimeType,modifiedTime,webViewLink,webContentLink,description"
            ).execute()
            
            return True, {
                "id": file_info['id'],
                "name": file_info['name'],
                "size": int(file_info.get('size', 0)) if file_info.get('size') else None,
                "last_modified": file_info.get('modifiedTime'),
                "content_type": file_info.get('mimeType'),
                "description": file_info.get('description', ''),
                "url": f"https://drive.google.com/uc?id={file_id}&export=download",
                "view_url": file_info.get('webViewLink', '')
            }
            
        except HttpError as e:
            logger.error(f"Google Drive HTTP error getting file info for {file_id}: {e}")
            return False, {"error": f"Drive API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error getting file info for {file_id}: {e}")
            return False, {"error": "Get info failed"}
    
    def download_file(self, file_id: str) -> Tuple[bool, bytes]:
        """
        Download file content from Google Drive
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Tuple of (success: bool, file_content: bytes)
        """
        if not self.is_configured():
            return False, b""
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return True, file_content.getvalue()
            
        except HttpError as e:
            logger.error(f"Google Drive HTTP error downloading file {file_id}: {e}")
            return False, b""
        except Exception as e:
            logger.error(f"Unexpected error downloading file {file_id}: {e}")
            return False, b""
    
    def _is_allowed_file(self, filename: str) -> bool:
        """Check if file type is allowed"""
        ALLOWED_EXTENSIONS = {
            'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff',  # Images
            'mp4', 'mov', 'avi', 'wmv', 'flv', 'webm',           # Videos
            'pdf', 'doc', 'docx', 'txt',                         # Documents
            'zip', 'rar', '7z'                                   # Archives
        }
        
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def _generate_file_name(self, filename: str, folder: str, custom_name: str = None) -> str:
        """Generate a unique file name for Google Drive"""
        if custom_name:
            base_name = secure_filename(custom_name)
        else:
            base_name = secure_filename(filename)
        
        # Extract extension
        if '.' in base_name:
            name, ext = base_name.rsplit('.', 1)
            ext = ext.lower()
        else:
            name = base_name
            ext = 'bin'
        
        # Generate unique name
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        
        drive_filename = f"{name}_{timestamp}_{unique_id}.{ext}"
        
        # Add folder prefix if specified
        if folder:
            folder = folder.strip('/')
            drive_filename = f"{folder}_{drive_filename}"
        
        return drive_filename

    def create_folder(self, folder_name: str, parent_id: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new folder in Google Drive
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Parent folder ID (uses main folder if None)
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        if not self.is_configured():
            return False, {"error": "Google Drive not configured"}
        
        try:
            parent_folder = parent_id or self.folder_id
            
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder]
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id,name'
            ).execute()
            
            logger.info(f"Folder created successfully: {folder_name} (ID: {folder['id']})")
            
            return True, {
                "folder_id": folder['id'],
                "folder_name": folder['name']
            }
            
        except HttpError as e:
            logger.error(f"Google Drive HTTP error creating folder {folder_name}: {e}")
            return False, {"error": f"Drive API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error creating folder {folder_name}: {e}")
            return False, {"error": "Folder creation failed"}

# Global instance
drive_storage_service = GoogleDriveService()

# Backward compatibility aliases
blob_storage_service = drive_storage_service  # For easy replacement
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
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

# Preferred Drive scopes (full access to avoid 404 on folders not created by the service)
PRIMARY_DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
FALLBACK_DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']  # legacy limited scope

# Environment variable names for optional advanced features
ENV_SHARED_DRIVE_ID = 'GOOGLE_DRIVE_SHARED_DRIVE_ID'  # If set, treat folder as inside this Shared Drive
ENV_IMPERSONATE_SUBJECT = 'GOOGLE_DRIVE_DELEGATED_USER'  # For domain-wide delegation (subject email)

logger = logging.getLogger(__name__)

class GoogleDriveService:
    """Enhanced Google Drive storage service with error handling and features"""
    
    def __init__(self):
        self.service = None
        self.folder_id = None
        self._initialized = False
        self._credentials = None
        self.shared_drive_id: Optional[str] = None
        self.delegated_user: Optional[str] = None
    
    def init_app(self, app):
        """Initialize with Flask app configuration"""
        try:
            # Check for Google Drive configuration
            folder_id = app.config.get('GOOGLE_DRIVE_FOLDER_ID')
            credentials_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            self.shared_drive_id = os.environ.get(ENV_SHARED_DRIVE_ID) or app.config.get('GOOGLE_DRIVE_SHARED_DRIVE_ID')
            self.delegated_user = os.environ.get(ENV_IMPERSONATE_SUBJECT) or app.config.get('GOOGLE_DRIVE_DELEGATED_USER')
            
            if not folder_id:
                logger.warning("Google Drive not configured - missing GOOGLE_DRIVE_FOLDER_ID")
                self._initialized = False
                return
            
            # Initialize credentials using GOOGLE_APPLICATION_CREDENTIALS
            if credentials_file and os.path.exists(credentials_file):
                # Use the standard Google credentials file
                try:
                    self._credentials = ServiceAccountCredentials.from_service_account_file(
                        credentials_file,
                        scopes=PRIMARY_DRIVE_SCOPES
                    )
                    # Domain-wide delegation / impersonation if configured
                    if self.delegated_user and hasattr(self._credentials, 'with_subject'):
                        self._credentials = self._credentials.with_subject(self.delegated_user)
                        logger.info(f"Applied domain-wide delegation for user: {self.delegated_user}")
                    logger.info(f"Using Google credentials from file with full drive scope: {credentials_file}")
                except Exception as e:
                    logger.warning(f"Failed to init credentials with full scope, retrying with drive.file: {e}")
                    self._credentials = ServiceAccountCredentials.from_service_account_file(
                        credentials_file,
                        scopes=FALLBACK_DRIVE_SCOPES
                    )
                    if self.delegated_user and hasattr(self._credentials, 'with_subject'):
                        self._credentials = self._credentials.with_subject(self.delegated_user)
                    logger.info("Initialized credentials with limited drive.file scope")
            else:
                # Fallback to JSON string method for backward compatibility
                credentials_json = app.config.get('GOOGLE_DRIVE_CREDENTIALS_JSON')
                if not credentials_json:
                    logger.warning("Google Drive not configured - no credentials found")
                    self._initialized = False
                    return
                
                if isinstance(credentials_json, str):
                    try:
                        creds_data = json.loads(credentials_json)
                    except json.JSONDecodeError:
                        with open(credentials_json, 'r') as f:
                            creds_data = json.load(f)
                else:
                    creds_data = credentials_json
                
                try:
                    self._credentials = ServiceAccountCredentials.from_service_account_info(
                        creds_data,
                        scopes=PRIMARY_DRIVE_SCOPES
                    )
                    if self.delegated_user and hasattr(self._credentials, 'with_subject'):
                        self._credentials = self._credentials.with_subject(self.delegated_user)
                    logger.info("Using Google credentials from JSON configuration (full drive scope)")
                except Exception as e:
                    logger.warning(f"Full scope auth failed, falling back to drive.file: {e}")
                    self._credentials = ServiceAccountCredentials.from_service_account_info(
                        creds_data,
                        scopes=FALLBACK_DRIVE_SCOPES
                    )
                    if self.delegated_user and hasattr(self._credentials, 'with_subject'):
                        self._credentials = self._credentials.with_subject(self.delegated_user)
                    logger.info("Using Google credentials with limited drive.file scope")
            
            # Build the Drive API service
            self.service = build('drive', 'v3', credentials=self._credentials)
            self.folder_id = folder_id
            
            # Verify folder exists and is accessible
            self._verify_folder_access()

            if self.shared_drive_id:
                logger.info(f"Shared Drive mode enabled (driveId={self.shared_drive_id})")
            if self.delegated_user:
                logger.info(f"Delegated (impersonated) user: {self.delegated_user}")
            
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
            create_kwargs = {
                'body': file_metadata,
                'media_body': media,
                'fields': 'id,name,size,mimeType,webViewLink,webContentLink'
            }
            # Shared Drive support parameters
            if self.shared_drive_id:
                create_kwargs['supportsAllDrives'] = True
            uploaded_file = self.service.files().create(**create_kwargs).execute()
            
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
                "blob_name": drive_filename,  # For compatibility
                "public_url": public_url,
                "url": public_url,  # For compatibility
                "view_url": uploaded_file.get('webViewLink', ''),
                "size": uploaded_file.get('size', len(file_content)),
                "content_type": mime_type,
                "folder": folder
            }
            
        except HttpError as e:
            quota_hint = None
            if e.resp is not None and e.resp.status in (403, 404):
                # Attempt to parse known quota errors
                try:
                    err_content = json.loads(e.content.decode()) if hasattr(e, 'content') else {}
                    reason_list = err_content.get('error', {}).get('errors', [])
                    for r in reason_list:
                        if r.get('reason') in ('storageQuotaExceeded', 'teamDriveFileLimitExceeded'):
                            quota_hint = (
                                "Service account personal storage is exhausted or unavailable. "
                                "Move target folder into a Shared Drive and set GOOGLE_DRIVE_SHARED_DRIVE_ID, "
                                "or enable domain-wide delegation with GOOGLE_DRIVE_DELEGATED_USER."
                            )
                            break
                except Exception:
                    pass
            logger.error(f"Google Drive HTTP error uploading file: {e}; quota_hint={quota_hint}")
            err_msg = f"Drive API error: {str(e)}"
            if quota_hint:
                err_msg += f" | {quota_hint}"
            return False, {"error": err_msg}
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
            # Validate folder id
            if not self.folder_id or ' ' in self.folder_id:
                logger.error(f"Invalid folder id format: '{self.folder_id}'")
                return False, {"error": "Invalid folder ID configured"}

            # Build query (always quote the folder ID)
            query = f"'{self.folder_id}' in parents and trashed=false"
            if folder:
                safe_folder = folder.replace("'", "\'")
                query += f" and name contains '{safe_folder}'"

            logger.debug(f"Drive list query: {query}")
            
            # List files
            list_kwargs = {
                'q': query,
                'pageSize': min(limit, 1000),
                'fields': "files(id,name,size,mimeType,modifiedTime,webViewLink,webContentLink)"
            }
            if self.shared_drive_id:
                list_kwargs.update({
                    'supportsAllDrives': True,
                    'includeItemsFromAllDrives': True,
                    'corpora': 'drive',
                    'driveId': self.shared_drive_id
                })
            results = self.service.files().list(**list_kwargs).execute()
            
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
            get_kwargs = {
                'fileId': file_id,
                'fields': "id,name,size,mimeType,modifiedTime,webViewLink,webContentLink,description"
            }
            if self.shared_drive_id:
                get_kwargs['supportsAllDrives'] = True
            file_info = self.service.files().get(**get_kwargs).execute()
            
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
            get_media_kwargs = {'fileId': file_id}
            if self.shared_drive_id:
                get_media_kwargs['supportsAllDrives'] = True
            request = self.service.files().get_media(**get_media_kwargs)
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

    # Video-specific methods for backward compatibility
    def upload_video(self, file_path, filename, title=None):
        """
        Upload a video file to Google Drive (backward compatibility)
        
        Args:
            file_path: Path to the video file
            filename: Name for the file in Google Drive
            title: Optional title/description
        
        Returns:
            dict: {'success': bool, 'file_id': str, 'error': str}
        """
        if not self.is_configured():
            return {'success': False, 'error': 'Google Drive not configured'}
        
        try:
            # File metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            if title:
                file_metadata['description'] = title
            
            # Upload file
            media = MediaFileUpload(
                file_path,
                mimetype='video/mp4',
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            # Make file publicly viewable
            self.make_file_public(file['id'])
            
            logger.info(f"Uploaded video to Google Drive: {file['id']}")
            
            return {
                'success': True,
                'file_id': file['id'],
                'name': file['name'],
                'web_view_link': file.get('webViewLink')
            }
            
        except Exception as e:
            logger.error(f"Failed to upload video to Google Drive: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def make_file_public(self, file_id):
        """Make a Google Drive file publicly viewable"""
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
        except Exception as e:
            logger.warning(f"Could not make file public: {str(e)}")
    
    def get_streaming_url(self, file_id):
        """
        Get direct streaming URL for a video file
        Note: This creates a direct download link that can be used for video streaming
        """
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    def list_videos(self):
        """List all videos in the configured folder"""
        if not self.is_configured():
            return []
        
        try:
            query = f"'{self.folder_id}' in parents and mimeType contains 'video/'"
            
            list_kwargs = {
                'q': query,
                'fields': "files(id,name,size,mimeType,thumbnailLink,createdTime)"
            }
            if self.shared_drive_id:
                list_kwargs.update({
                    'supportsAllDrives': True,
                    'includeItemsFromAllDrives': True,
                    'corpora': 'drive',
                    'driveId': self.shared_drive_id
                })
            results = self.service.files().list(**list_kwargs).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            logger.error(f"Failed to list videos: {str(e)}")
            return []

# Global instance
drive_service = GoogleDriveService()

# Backward compatibility alias for upload routes
drive_storage_service = drive_service
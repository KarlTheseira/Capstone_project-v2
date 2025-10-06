"""
Google Drive integration for video hosting
"""
import os
import json
from flask import current_app
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
import tempfile

class GoogleDriveService:
    def __init__(self):
        self.service = None
        self.folder_id = None
    
    def init_app(self, app):
        """Initialize Google Drive service with Flask app"""
        with app.app_context():
            try:
                # Get credentials from environment or config
                credentials_json = app.config.get('GOOGLE_DRIVE_CREDENTIALS_JSON')
                self.folder_id = app.config.get('GOOGLE_DRIVE_FOLDER_ID')
                
                if not credentials_json or not self.folder_id:
                    current_app.logger.warning("Google Drive not configured - missing credentials or folder ID")
                    return
                
                # Parse credentials
                if isinstance(credentials_json, str):
                    try:
                        credentials_info = json.loads(credentials_json)
                    except json.JSONDecodeError:
                        current_app.logger.error("Invalid Google Drive credentials JSON format")
                        return
                else:
                    credentials_info = credentials_json
                
                # Create credentials
                credentials = Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                
                # Build the service
                self.service = build('drive', 'v3', credentials=credentials)
                current_app.logger.info("Google Drive service initialized successfully")
                
            except Exception as e:
                current_app.logger.error(f"Failed to initialize Google Drive service: {str(e)}")
                self.service = None
    
    def is_configured(self):
        """Check if Google Drive is properly configured"""
        return self.service is not None and self.folder_id is not None
    
    def upload_video(self, file_path, filename, title=None):
        """
        Upload a video file to Google Drive
        
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
            
            current_app.logger.info(f"Uploaded video to Google Drive: {file['id']}")
            
            return {
                'success': True,
                'file_id': file['id'],
                'name': file['name'],
                'web_view_link': file.get('webViewLink')
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to upload video to Google Drive: {str(e)}")
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
            current_app.logger.warning(f"Could not make file public: {str(e)}")
    
    def delete_file(self, file_id):
        """Delete a file from Google Drive"""
        if not self.is_configured():
            return {'success': False, 'error': 'Google Drive not configured'}
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            current_app.logger.info(f"Deleted file from Google Drive: {file_id}")
            return {'success': True}
            
        except Exception as e:
            current_app.logger.error(f"Failed to delete file from Google Drive: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_file_info(self, file_id):
        """Get information about a Google Drive file"""
        if not self.is_configured():
            return None
        
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id,name,size,mimeType,webViewLink,thumbnailLink'
            ).execute()
            
            return file
            
        except Exception as e:
            current_app.logger.error(f"Failed to get file info: {str(e)}")
            return None
    
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
            
            results = self.service.files().list(
                q=query,
                fields="files(id,name,size,mimeType,thumbnailLink,createdTime)"
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            current_app.logger.error(f"Failed to list videos: {str(e)}")
            return []

# Global instance
drive_service = GoogleDriveService()
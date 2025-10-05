import azure.functions as func
import logging
import json
import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Google Drive Manager Azure Function
    
    Handles Google Drive operations:
    - GET: List files, get file info
    - POST: Upload files, create folders
    - DELETE: Delete files
    """
    
    logging.info(f'📁 Google Drive Manager triggered: {req.method} {req.url}')
    
    try:
        # Initialize Google Drive service
        drive_service = initialize_drive_service()
        if not drive_service:
            return func.HttpResponse(
                json.dumps({"error": "Google Drive service not configured"}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Route based on HTTP method
        if req.method == 'GET':
            return handle_get_request(req, drive_service)
        elif req.method == 'POST':
            return handle_post_request(req, drive_service)
        elif req.method == 'DELETE':
            return handle_delete_request(req, drive_service)
        else:
            return func.HttpResponse(
                json.dumps({"error": "Method not allowed"}),
                status_code=405,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"💥 Error in Google Drive Manager: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def initialize_drive_service():
    """Initialize Google Drive API service"""
    
    try:
        credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_JSON')
        if not credentials_json:
            logging.error("GOOGLE_DRIVE_CREDENTIALS_JSON not configured")
            return None
        
        # Parse credentials
        creds_data = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build Drive service
        service = build('drive', 'v3', credentials=credentials)
        return service
        
    except Exception as e:
        logging.error(f"Failed to initialize Drive service: {e}")
        return None


def handle_get_request(req: func.HttpRequest, service) -> func.HttpResponse:
    """Handle GET requests - list files, get file info"""
    
    try:
        # Parse query parameters
        action = req.params.get('action', 'list')
        file_id = req.params.get('file_id')
        folder_id = req.params.get('folder_id', os.environ.get('GOOGLE_DRIVE_FOLDER_ID'))
        limit = int(req.params.get('limit', 100))
        
        if action == 'list':
            return list_drive_files(service, folder_id, limit)
        elif action == 'info' and file_id:
            return get_file_info(service, file_id)
        elif action == 'download' and file_id:
            return download_file(service, file_id)
        else:
            return func.HttpResponse(
                json.dumps({"error": "Invalid action or missing parameters"}),
                status_code=400,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"Error in GET request: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_post_request(req: func.HttpRequest, service) -> func.HttpResponse:
    """Handle POST requests - upload files, create folders"""
    
    try:
        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON payload"}),
                status_code=400,
                mimetype="application/json"
            )
        
        action = req_body.get('action', 'upload')
        
        if action == 'upload':
            return upload_file_to_drive(service, req_body)
        elif action == 'create_folder':
            return create_drive_folder(service, req_body)
        elif action == 'batch_upload':
            return batch_upload_files(service, req_body)
        else:
            return func.HttpResponse(
                json.dumps({"error": "Invalid action"}),
                status_code=400,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"Error in POST request: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_delete_request(req: func.HttpRequest, service) -> func.HttpResponse:
    """Handle DELETE requests - delete files"""
    
    try:
        file_id = req.params.get('file_id')
        if not file_id:
            return func.HttpResponse(
                json.dumps({"error": "file_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        return delete_drive_file(service, file_id)
        
    except Exception as e:
        logging.error(f"Error in DELETE request: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def list_drive_files(service, folder_id, limit):
    """List files in Google Drive folder"""
    
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        
        results = service.files().list(
            q=query,
            pageSize=min(limit, 1000),
            fields="files(id,name,size,mimeType,modifiedTime,webViewLink),nextPageToken"
        ).execute()
        
        files = []
        for file_item in results.get('files', []):
            files.append({
                "id": file_item['id'],
                "name": file_item['name'],
                "size": int(file_item.get('size', 0)) if file_item.get('size') else None,
                "mime_type": file_item.get('mimeType'),
                "modified_time": file_item.get('modifiedTime'),
                "view_link": file_item.get('webViewLink'),
                "download_url": f"https://drive.google.com/uc?id={file_item['id']}&export=download"
            })
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "files": files,
                "total": len(files),
                "folder_id": folder_id
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except HttpError as e:
        logging.error(f"Drive API error listing files: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Drive API error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


def get_file_info(service, file_id):
    """Get information about a specific file"""
    
    try:
        file_info = service.files().get(
            fileId=file_id,
            fields="id,name,size,mimeType,modifiedTime,webViewLink,description,parents"
        ).execute()
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "file": {
                    "id": file_info['id'],
                    "name": file_info['name'],
                    "size": int(file_info.get('size', 0)) if file_info.get('size') else None,
                    "mime_type": file_info.get('mimeType'),
                    "modified_time": file_info.get('modifiedTime'),
                    "view_link": file_info.get('webViewLink'),
                    "description": file_info.get('description', ''),
                    "parents": file_info.get('parents', []),
                    "download_url": f"https://drive.google.com/uc?id={file_id}&export=download"
                }
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except HttpError as e:
        logging.error(f"Drive API error getting file info: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Drive API error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


def upload_file_to_drive(service, req_body):
    """Upload a file to Google Drive from base64 data"""
    
    try:
        import base64
        
        filename = req_body.get('filename')
        file_data_b64 = req_body.get('file_data')
        folder_id = req_body.get('folder_id', os.environ.get('GOOGLE_DRIVE_FOLDER_ID'))
        mime_type = req_body.get('mime_type', 'application/octet-stream')
        
        if not filename or not file_data_b64:
            return func.HttpResponse(
                json.dumps({"error": "filename and file_data required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Decode base64 data
        file_data = base64.b64decode(file_data_b64)
        
        # Create file metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id],
            'description': f"Uploaded via Azure Function on {func.datetime.utcnow().isoformat()}"
        }
        
        # Create media upload
        media = MediaIoBaseUpload(
            io.BytesIO(file_data),
            mimetype=mime_type,
            resumable=True
        )
        
        # Upload file
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,size,webViewLink'
        ).execute()
        
        # Make file publicly viewable
        try:
            service.permissions().create(
                fileId=uploaded_file['id'],
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
        except:
            logging.warning(f"Could not make file public: {uploaded_file['id']}")
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "file": {
                    "id": uploaded_file['id'],
                    "name": uploaded_file['name'],
                    "size": uploaded_file.get('size'),
                    "view_link": uploaded_file.get('webViewLink'),
                    "download_url": f"https://drive.google.com/uc?id={uploaded_file['id']}&export=download"
                }
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error uploading file: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def create_drive_folder(service, req_body):
    """Create a new folder in Google Drive"""
    
    try:
        folder_name = req_body.get('folder_name')
        parent_id = req_body.get('parent_id', os.environ.get('GOOGLE_DRIVE_FOLDER_ID'))
        
        if not folder_name:
            return func.HttpResponse(
                json.dumps({"error": "folder_name required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        
        folder = service.files().create(
            body=folder_metadata,
            fields='id,name'
        ).execute()
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "folder": {
                    "id": folder['id'],
                    "name": folder['name'],
                    "parent_id": parent_id
                }
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error creating folder: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def delete_drive_file(service, file_id):
    """Delete a file from Google Drive"""
    
    try:
        # Get file name for logging
        try:
            file_info = service.files().get(fileId=file_id, fields='name').execute()
            filename = file_info.get('name', 'Unknown')
        except:
            filename = 'Unknown'
        
        # Delete the file
        service.files().delete(fileId=file_id).execute()
        
        logging.info(f"File deleted: {filename} (ID: {file_id})")
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "message": f"File '{filename}' deleted successfully",
                "file_id": file_id
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except HttpError as e:
        logging.error(f"Drive API error deleting file: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Drive API error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


def batch_upload_files(service, req_body):
    """Upload multiple files in batch"""
    
    try:
        files_data = req_body.get('files', [])
        folder_id = req_body.get('folder_id', os.environ.get('GOOGLE_DRIVE_FOLDER_ID'))
        
        if not files_data:
            return func.HttpResponse(
                json.dumps({"error": "files array required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        results = []
        
        for file_info in files_data:
            try:
                # Upload individual file (simplified version)
                result = upload_file_to_drive(service, {
                    **file_info,
                    'folder_id': folder_id
                })
                
                if result.status_code == 200:
                    results.append({
                        "filename": file_info.get('filename'),
                        "success": True,
                        "result": json.loads(result.get_body().decode())
                    })
                else:
                    results.append({
                        "filename": file_info.get('filename'),
                        "success": False,
                        "error": "Upload failed"
                    })
                    
            except Exception as e:
                results.append({
                    "filename": file_info.get('filename', 'Unknown'),
                    "success": False,
                    "error": str(e)
                })
        
        successful_uploads = sum(1 for r in results if r["success"])
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "total_files": len(files_data),
                "successful_uploads": successful_uploads,
                "failed_uploads": len(files_data) - successful_uploads,
                "results": results
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in batch upload: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
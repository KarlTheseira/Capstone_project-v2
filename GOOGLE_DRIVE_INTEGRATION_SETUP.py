# Add these configuration updates to your Flask app

# 1. In config.py, add Google Drive configuration
GOOGLE_DRIVE_CONFIGURATION = """
# Google Drive Configuration
GOOGLE_DRIVE_CREDENTIALS_JSON = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_JSON')
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')

# Enable dual storage (Google Drive + Azure Blob)
ENABLE_DUAL_STORAGE = os.environ.get('ENABLE_DUAL_STORAGE', 'false').lower() == 'true'

# Storage preference: 'google_drive', 'azure', 'both'
DEFAULT_STORAGE = os.environ.get('DEFAULT_STORAGE', 'google_drive')
"""

# 2. In app.py, register the enhanced upload blueprint
APP_BLUEPRINT_REGISTRATION = """
# Import enhanced upload routes
from routes.enhanced_upload import enhanced_upload_bp

# Register enhanced upload blueprint
app.register_blueprint(enhanced_upload_bp)

# Initialize Google Drive service with app
from utils.google_drive import drive_storage_service
drive_storage_service.init_app(app)
"""

# 3. Add to your environment variables (.env file)
ENVIRONMENT_VARIABLES = """
# Google Drive Configuration
GOOGLE_DRIVE_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project-id","private_key_id":"key-id","private_key":"-----BEGIN PRIVATE KEY-----\\nYOUR-PRIVATE-KEY\\n-----END PRIVATE KEY-----\\n","client_email":"your-service-account@project.iam.gserviceaccount.com","client_id":"123456789","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40project.iam.gserviceaccount.com"}
GOOGLE_DRIVE_FOLDER_ID=your-google-drive-folder-id

# Storage Settings
ENABLE_DUAL_STORAGE=true
DEFAULT_STORAGE=google_drive

# Azure Functions URL (for image processing)
AZURE_FUNCTIONS_URL=https://flashstudio-functions.azurewebsites.net
"""

# 4. Database model for tracking uploads (add to models.py)
DATABASE_MODEL = """
class FileUpload(db.Model):
    __tablename__ = 'file_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    folder = db.Column(db.String(100))
    
    # Google Drive references
    google_drive_id = db.Column(db.String(100))
    google_drive_url = db.Column(db.String(500))
    
    # Azure Blob references
    azure_blob_name = db.Column(db.String(255))
    azure_blob_url = db.Column(db.String(500))
    
    # File metadata
    file_size = db.Column(db.Integer)
    content_type = db.Column(db.String(100))
    
    # Processing status
    processing_status = db.Column(db.String(50), default='none')  # none, pending, completed, failed
    processed_versions = db.Column(db.Text)  # JSON string of processed versions
    
    # Timestamps
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime)
    
    # Relationships (optional)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'folder': self.folder,
            'google_drive_id': self.google_drive_id,
            'google_drive_url': self.google_drive_url,
            'azure_blob_name': self.azure_blob_name,
            'azure_blob_url': self.azure_blob_url,
            'file_size': self.file_size,
            'content_type': self.content_type,
            'processing_status': self.processing_status,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }
"""
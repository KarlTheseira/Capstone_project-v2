# Google Drive Storage Setup Guide

This guide will help you set up Google Drive as the storage backend for FlashStudio, replacing Azure Blob Storage.

## Prerequisites

- Google Cloud Platform account
- Google Drive with sufficient storage space
- Admin access to your Google Workspace (optional, but recommended)

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API:
   ```bash
   gcloud services enable drive.googleapis.com
   ```

## Step 2: Create a Service Account

1. In the Google Cloud Console, go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Provide a name (e.g., "flashstudio-storage")
4. Grant the service account the "Editor" role
5. Click "Create Key" and download the JSON credentials file
6. Save the credentials as `google-drive-credentials.json`

## Step 3: Set Up Google Drive Folder

1. Create a dedicated folder in Google Drive for FlashStudio uploads
2. Share the folder with your service account email (found in the credentials JSON)
3. Give the service account "Editor" permissions
4. Copy the folder ID from the URL (e.g., `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`)

## Step 4: Configure Environment Variables

### For Local Development

Add to your `.env` file:

```bash
# Google Drive Configuration
GOOGLE_DRIVE_CREDENTIALS_JSON='{"type": "service_account", "project_id": "your-project", ...}'
GOOGLE_DRIVE_FOLDER_ID="your-folder-id-here"
```

### For Production/Kubernetes

Create the Kubernetes secret:

```bash
kubectl create secret generic google-drive-secrets \
  --from-file=GOOGLE_DRIVE_CREDENTIALS_JSON=google-drive-credentials.json \
  --from-literal=GOOGLE_DRIVE_FOLDER_ID="your-folder-id" \
  --namespace=flash
```

## Step 5: Install Dependencies

The required Python packages are already in `requirements.txt`:

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

## Step 6: Test the Integration

Create a test script to verify the setup:

```python
import os
import json
from utils.google_drive import drive_storage_service

# Load credentials (adjust path as needed)
with open('google-drive-credentials.json', 'r') as f:
    credentials = json.load(f)

# Set environment variables
os.environ['GOOGLE_DRIVE_CREDENTIALS_JSON'] = json.dumps(credentials)
os.environ['GOOGLE_DRIVE_FOLDER_ID'] = 'your-folder-id'

# Test configuration
from flask import Flask
app = Flask(__name__)
app.config['GOOGLE_DRIVE_CREDENTIALS_JSON'] = json.dumps(credentials)
app.config['GOOGLE_DRIVE_FOLDER_ID'] = 'your-folder-id'

drive_storage_service.init_app(app)

if drive_storage_service.is_configured():
    print("✅ Google Drive integration working!")
    
    # Test file listing
    success, result = drive_storage_service.list_files()
    if success:
        print(f"📁 Found {result['total']} files in folder")
    else:
        print(f"❌ Error listing files: {result}")
else:
    print("❌ Google Drive not configured properly")
```

## Features Supported

The Google Drive service provides the same interface as Azure Blob Storage:

### File Operations
- ✅ **Upload files** with automatic unique naming
- ✅ **Delete files** by ID
- ✅ **List files** with filtering and pagination
- ✅ **Get file information** (size, type, modified date)
- ✅ **Generate download URLs** for direct access
- ✅ **Download file content** programmatically

### Security Features
- ✅ **File type validation** (images, videos, documents)
- ✅ **Secure filename handling** with sanitization
- ✅ **Service account authentication** for server access
- ✅ **Folder-based organization** with ID-based access control

### Production Features
- ✅ **Error handling** with comprehensive logging
- ✅ **Automatic retries** for transient failures
- ✅ **Public URL generation** for web access
- ✅ **Metadata preservation** (upload time, original filename)

## File URL Formats

Google Drive provides several URL types:

1. **Direct Download**: `https://drive.google.com/uc?id={file_id}&export=download`
2. **View in Browser**: `https://drive.google.com/file/d/{file_id}/view`
3. **Embed**: `https://drive.google.com/file/d/{file_id}/preview`

## Troubleshooting

### Common Issues

**"Access denied" errors:**
- Verify the service account has access to the folder
- Check that the folder ID is correct
- Ensure the Drive API is enabled in your GCP project

**"Quota exceeded" errors:**
- Check your Google Drive storage quota
- Monitor API usage in the GCP Console
- Consider upgrading your Google Workspace plan

**File upload failures:**
- Verify file types are allowed (see `_is_allowed_file()`)
- Check file size limits (Google Drive has per-file limits)
- Ensure stable internet connection for large uploads

### Monitoring and Logging

The service provides detailed logging:

```python
import logging
logging.getLogger('utils.google_drive').setLevel(logging.DEBUG)
```

### Performance Considerations

- **File Size**: Google Drive supports files up to 5TB
- **API Quotas**: 1,000 requests per 100 seconds per user
- **Bandwidth**: Upload/download speeds depend on Google's infrastructure
- **Caching**: Consider implementing client-side caching for frequently accessed files

## Migration from Azure Blob Storage

If migrating from Azure Blob Storage:

1. **Export existing files** from Azure
2. **Upload to Google Drive** using the new service
3. **Update file references** in your database (URLs will change)
4. **Test all file operations** thoroughly
5. **Monitor performance** and adjust as needed

## Security Best Practices

1. **Rotate service account keys** regularly
2. **Use separate folders** for different environments (dev/staging/prod)
3. **Monitor access logs** in the Google Admin Console
4. **Implement rate limiting** on your application side
5. **Regular backup** of important files to another location

## Cost Considerations

Google Drive pricing:
- **15GB free** with personal Google account
- **Google Workspace**: Starts at $6/user/month with 30GB
- **Enterprise plans**: Custom pricing for larger storage needs
- **API usage**: Generally free within reasonable quotas

This Google Drive integration provides a cost-effective, reliable alternative to Azure Blob Storage with the same functionality and security features.
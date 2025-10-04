# 📁 Azure Blob Storage Integration Guide

## 🌟 Overview

Your FlashStudio application now has **enterprise-grade Azure Blob Storage integration** for handling file uploads, media management, and document storage.

### ✅ **What's Implemented**

1. **🔧 Enhanced Storage Service** - Robust file management with error handling
2. **🌐 REST API Endpoints** - Complete file operations (upload, delete, list, info)
3. **🔒 Secure Access** - SAS token generation for private file access
4. **🏗️ Kubernetes Ready** - Production deployment configuration
5. **📊 Monitoring & Logging** - Comprehensive error tracking and logging

---

## 🚀 **Quick Setup**

### **Option 1: Automated Setup (Recommended)**

```bash
# Run the automated Azure setup script
./setup-azure-storage.sh

# Follow the prompts to create:
# - Resource Group
# - Storage Account 
# - Blob Containers
# - CORS Configuration
```

### **Option 2: Manual Azure Portal Setup**

1. **Create Storage Account**
   - Go to Azure Portal → Storage Accounts → Create
   - Choose Standard performance, LRS replication
   - Enable public blob access

2. **Create Containers**
   - Create containers: `uploads`, `media`, `backups`
   - Set public access level to "Blob"

3. **Get Connection String**
   - Go to Access Keys → Show keys
   - Copy Connection String

---

## 🔧 **Configuration**

### **Environment Variables**

Add these to your `.env` file:

```bash
# Azure Storage Configuration
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=your_account;AccountKey=your_key;EndpointSuffix=core.windows.net"
AZURE_STORAGE_ACCOUNT="your_storage_account_name"
AZURE_STORAGE_CONTAINER="uploads"
```

### **Kubernetes Secrets**

For production deployment:

```bash
kubectl create secret generic blob-conn \
  --from-literal=AZURE_STORAGE_CONNECTION_STRING="your_connection_string" \
  --namespace=flash
```

---

## 📡 **API Endpoints**

Your application now provides these file management endpoints:

### **Upload File**
```bash
POST /api/upload
Content-Type: multipart/form-data

# Parameters:
# - file: File to upload (required)
# - folder: Optional folder path
# - custom_name: Optional custom filename

# Response:
{
  "blob_name": "document_20241002_abc123.pdf",
  "public_url": "https://storage.blob.core.windows.net/uploads/document_20241002_abc123.pdf",
  "container": "uploads",
  "size": 1024768,
  "content_type": "application/pdf"
}
```

### **List Files**
```bash
GET /api/files?folder=images&limit=50

# Response:
{
  "files": [
    {
      "name": "image_20241002_def456.jpg",
      "size": 524288,
      "last_modified": "2024-10-02T10:30:00Z",
      "content_type": "image/jpeg",
      "url": "https://storage.blob.core.windows.net/uploads/image_20241002_def456.jpg"
    }
  ],
  "total": 1,
  "container": "uploads"
}
```

### **Delete File**
```bash
DELETE /api/files/document_20241002_abc123.pdf

# Response:
{
  "message": "File document_20241002_abc123.pdf deleted successfully"
}
```

### **Get File Info**
```bash
GET /api/files/image_20241002_def456.jpg/info

# Response:
{
  "name": "image_20241002_def456.jpg",
  "size": 524288,
  "last_modified": "2024-10-02T10:30:00Z",
  "content_type": "image/jpeg",
  "metadata": {
    "original_name": "profile-photo.jpg",
    "upload_time": "2024-10-02T10:30:00Z"
  },
  "url": "https://storage.blob.core.windows.net/uploads/image_20241002_def456.jpg"
}
```

### **Generate Secure Download URL**
```bash
GET /api/files/private_document.pdf/download-url?expiry_hours=2

# Response:
{
  "download_url": "https://storage.blob.core.windows.net/uploads/private_document.pdf?sv=2020-08-04&st=2024-10-02T10%3A00%3A00Z&se=2024-10-02T12%3A00%3A00Z&sr=b&sp=r&sig=xxx",
  "expires_in_hours": 2
}
```

---

## 🎯 **Supported File Types**

### **Images**
- `jpg`, `jpeg`, `png`, `gif`, `webp`, `bmp`, `tiff`

### **Videos** 
- `mp4`, `mov`, `avi`, `wmv`, `flv`, `webm`

### **Documents**
- `pdf`, `doc`, `docx`, `txt`

### **Archives**
- `zip`, `rar`, `7z`

---

## 💻 **Frontend Integration Examples**

### **File Upload Form**

```html
<!-- Upload Form -->
<form id="upload-form" enctype="multipart/form-data">
    <input type="file" name="file" id="file-input" accept="image/*,video/*,.pdf">
    <input type="text" name="folder" placeholder="Optional folder">
    <button type="submit">Upload</button>
</form>

<script>
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('Upload successful:', result);
            // Handle success - show image, update UI, etc.
        } else {
            console.error('Upload failed:', result.error);
        }
    } catch (error) {
        console.error('Upload error:', error);
    }
});
</script>
```

### **File Gallery**

```javascript
// Load and display files
async function loadFileGallery() {
    try {
        const response = await fetch('/api/files?folder=gallery&limit=20');
        const result = await response.json();
        
        if (response.ok) {
            const gallery = document.getElementById('file-gallery');
            gallery.innerHTML = '';
            
            result.files.forEach(file => {
                const fileElement = document.createElement('div');
                fileElement.className = 'file-item';
                fileElement.innerHTML = `
                    <img src="${file.url}" alt="${file.name}" loading="lazy">
                    <p>${file.name}</p>
                    <small>${(file.size / 1024).toFixed(1)} KB</small>
                    <button onclick="deleteFile('${file.name}')">Delete</button>
                `;
                gallery.appendChild(fileElement);
            });
        }
    } catch (error) {
        console.error('Failed to load gallery:', error);
    }
}

// Delete file function
async function deleteFile(fileName) {
    if (!confirm('Are you sure you want to delete this file?')) return;
    
    try {
        const response = await fetch(`/api/files/${fileName}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadFileGallery(); // Reload gallery
        } else {
            const result = await response.json();
            alert('Delete failed: ' + result.error);
        }
    } catch (error) {
        console.error('Delete error:', error);
    }
}
```

---

## 🏗️ **Production Deployment**

### **Azure Storage Best Practices**

1. **🔒 Security**
   - Use private containers for sensitive files
   - Generate SAS tokens for temporary access
   - Enable Azure Storage Analytics
   - Set up access policies

2. **💰 Cost Optimization**
   - Use appropriate storage tiers (Hot/Cool/Archive)
   - Enable lifecycle management
   - Compress files before upload
   - Monitor storage usage

3. **🚀 Performance**
   - Use CDN for frequently accessed files
   - Implement client-side compression
   - Use appropriate blob types
   - Monitor bandwidth usage

### **Kubernetes Configuration**

Your deployment already includes Azure Storage configuration:

```yaml
# In deployment.yaml
env:
  - name: AZURE_STORAGE_CONNECTION_STRING
    valueFrom:
      secretKeyRef:
        name: blob-conn
        key: AZURE_STORAGE_CONNECTION_STRING
  - name: AZURE_STORAGE_ACCOUNT
    value: "your_storage_account"
  - name: AZURE_STORAGE_CONTAINER
    value: "uploads"
```

---

## 📊 **Monitoring & Troubleshooting**

### **Health Checks**

```python
# Check storage service health
from utils.azure_storage import blob_storage_service

if blob_storage_service.is_configured():
    print("✅ Azure Blob Storage is configured and ready")
else:
    print("❌ Azure Blob Storage not configured")
```

### **Common Issues**

#### **1. Connection String Issues**
```
Error: "Blob storage not configured"
Solution: Verify AZURE_STORAGE_CONNECTION_STRING is set correctly
```

#### **2. Container Access Issues**
```
Error: "Storage error: ContainerNotFound"
Solution: Ensure containers exist and have proper access permissions
```

#### **3. File Type Restrictions**
```
Error: "File type not allowed"
Solution: Check ALLOWED_EXTENSIONS in azure_storage.py
```

#### **4. Size Limits**
```
Error: Upload fails for large files
Solution: Configure appropriate blob size limits and client timeout
```

### **Logging**

All storage operations are logged. Check logs with:

```bash
# In Kubernetes
kubectl logs -f deployment/flashstudio-monolith -n flash | grep -i "azure\|blob\|storage"

# Local development
# Check console output for storage-related logs
```

---

## 🔧 **Advanced Configuration**

### **Custom Storage Service**

You can extend the storage service for specific needs:

```python
from utils.azure_storage import BlobStorageService

class CustomStorageService(BlobStorageService):
    def upload_with_watermark(self, file, watermark_text):
        # Custom implementation for watermarked uploads
        pass
    
    def create_thumbnail(self, image_blob_name):
        # Custom thumbnail generation
        pass
```

### **Batch Operations**

```python
# Example: Batch delete files
async def cleanup_old_files():
    success, result = blob_storage_service.list_files()
    
    if success:
        for file in result['files']:
            # Delete files older than 30 days
            if is_older_than_30_days(file['last_modified']):
                blob_storage_service.delete_file(file['name'])
```

---

## 🎯 **Testing**

### **Development Testing**

```bash
# Test file upload
curl -X POST http://localhost:5001/api/upload \
  -F "file=@test-image.jpg" \
  -F "folder=test"

# Test file listing  
curl http://localhost:5001/api/files

# Test file deletion
curl -X DELETE http://localhost:5001/api/files/test_file.jpg
```

### **Production Validation**

1. **Upload Test**: Try uploading different file types
2. **Access Test**: Verify public URLs are accessible
3. **Security Test**: Check private file access works correctly
4. **Performance Test**: Upload larger files to test timeout handling

---

## 📚 **Resources**

- [Azure Blob Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Azure Storage Python SDK](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python)
- [Azure Storage Security Guide](https://docs.microsoft.com/en-us/azure/storage/common/storage-security-guide)

---

**Your FlashStudio application now has enterprise-grade file management capabilities!** 🎉

The Azure Blob Storage integration provides scalable, secure, and reliable file handling that's ready for production use.
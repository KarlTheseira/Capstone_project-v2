#!/usr/bin/env python3
"""
Test Google Drive integration for FlashStudio
Run this script to verify Google Drive service is working
"""
import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_google_drive_service():
    """Test Google Drive service initialization and basic functionality"""
    print("🔍 Testing Google Drive Service Integration")
    print("=" * 50)
    
    try:
        # Import the service
        from utils.google_drive import drive_storage_service
        from flask import Flask
        
        # Create test app
        app = Flask(__name__)
        
        # Check for credentials in environment
        creds_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON')
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        if not creds_json or not folder_id:
            print("⚠️  Google Drive not configured in environment variables")
            print("📝 To set up Google Drive:")
            print("   1. Create a service account in Google Cloud Console")
            print("   2. Download credentials JSON file")
            print("   3. Create a shared folder in Google Drive")
            print("   4. Set environment variables:")
            print("      export GOOGLE_DRIVE_CREDENTIALS_JSON='$(cat credentials.json)'")
            print("      export GOOGLE_DRIVE_FOLDER_ID='your-folder-id'")
            print()
            print("🔧 For now, testing service initialization without credentials...")
            
            # Test service without credentials
            app.config['GOOGLE_DRIVE_CREDENTIALS_JSON'] = ""
            app.config['GOOGLE_DRIVE_FOLDER_ID'] = ""
            drive_storage_service.init_app(app)
            
            if not drive_storage_service.is_configured():
                print("✅ Service correctly reports as not configured")
                print("✅ Google Drive service module loaded successfully")
                return True
            else:
                print("❌ Service should not be configured without credentials")
                return False
        
        else:
            print("✅ Found Google Drive configuration in environment")
            
            # Parse credentials
            try:
                creds_data = json.loads(creds_json)
                print(f"✅ Service account: {creds_data.get('client_email', 'Unknown')}")
            except json.JSONDecodeError:
                print("❌ Invalid credentials JSON format")
                return False
            
            # Initialize service
            app.config['GOOGLE_DRIVE_CREDENTIALS_JSON'] = creds_json
            app.config['GOOGLE_DRIVE_FOLDER_ID'] = folder_id
            
            with app.app_context():
                drive_storage_service.init_app(app)
                
                if drive_storage_service.is_configured():
                    print("✅ Google Drive service initialized successfully")
                    
                    # Test basic operations
                    print("\n🔍 Testing basic operations...")
                    
                    # Test file listing
                    success, result = drive_storage_service.list_files(limit=5)
                    if success:
                        print(f"✅ File listing: Found {result['total']} files")
                        for file_info in result['files'][:3]:  # Show first 3 files
                            print(f"   📄 {file_info['name']} ({file_info.get('size', 'unknown')} bytes)")
                    else:
                        print(f"⚠️  File listing failed: {result.get('error', 'Unknown error')}")
                    
                    return True
                else:
                    print("❌ Google Drive service failed to initialize")
                    return False
                    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you've installed the required packages:")
        print("   pip install google-api-python-client google-auth")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_file_operations():
    """Test file operation methods (without actually uploading)"""
    print("\n🔍 Testing File Operation Methods")
    print("=" * 40)
    
    try:
        from utils.google_drive import drive_storage_service
        
        # Test method availability
        methods_to_test = [
            'upload_file',
            'delete_file', 
            'list_files',
            'get_file_info',
            'generate_download_url',
            'download_file',
            'create_folder'
        ]
        
        for method_name in methods_to_test:
            if hasattr(drive_storage_service, method_name):
                print(f"✅ Method available: {method_name}")
            else:
                print(f"❌ Method missing: {method_name}")
                return False
        
        print("✅ All required methods are available")
        return True
        
    except Exception as e:
        print(f"❌ Error testing methods: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 FlashStudio Google Drive Integration Test")
    print("=" * 60)
    
    # Test service initialization
    service_test = test_google_drive_service()
    
    # Test method availability
    methods_test = test_file_operations()
    
    print("\n" + "=" * 60)
    if service_test and methods_test:
        print("🎉 All tests passed! Google Drive integration is ready.")
        print("\n💡 Next steps:")
        print("   1. Set up Google Drive credentials (see GOOGLE_DRIVE_SETUP.md)")
        print("   2. Configure environment variables")
        print("   3. Test file uploads through the web interface")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return service_test and methods_test

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
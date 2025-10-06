import os
import uuid
from werkzeug.datastructures import FileStorage

class LocalStorageService:
    """Simple local filesystem storage for development/testing.
    Stores files under a configured base directory and exposes relative media URLs.
    """
    def __init__(self, base_dir: str = 'static/uploads'):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def is_configured(self):  # parity with drive_service
        return True

    def upload_file(self, file_obj: FileStorage):
        try:
            original = file_obj.filename or 'upload.bin'
            ext = os.path.splitext(original)[1]
            fname = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(self.base_dir, fname)
            file_obj.save(path)
            return True, {
                'id': fname,
                'name': original,
                'stored_name': fname,
                'local_path': path,
                'public_url': f"/media/{fname}"
            }
        except Exception as e:
            return False, {'error': str(e)}

    def list_files(self, limit=20):
        try:
            items = []
            for name in sorted(os.listdir(self.base_dir))[:limit]:
                items.append({
                    'id': name,
                    'name': name,
                    'public_url': f"/media/{name}"
                })
            return True, {'files': items}
        except Exception as e:
            return False, {'error': str(e)}

    def delete_file(self, file_id: str):
        try:
            path = os.path.join(self.base_dir, file_id)
            if os.path.exists(path):
                os.remove(path)
                return True, {}
            return False, {'error': 'not_found'}
        except Exception as e:
            return False, {'error': str(e)}

local_storage_service = LocalStorageService()

import os
import shutil
import uuid
from typing import BinaryIO, Tuple
from app.core.config import settings
from app.core.exceptions import StorageException
from app.services.storage.base import StorageService


class LocalStorageService(StorageService):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: str = settings.LOCAL_STORAGE_DIR):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    async def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "uploads",
    ) -> Tuple[str, str]:
        try:
            target_folder = os.path.join(self.base_dir, folder)
            os.makedirs(target_folder, exist_ok=True)
            
            ext = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(target_folder, unique_filename)
            
            # Write file bytes
            with open(file_path, "wb") as buffer:
                if hasattr(file_obj, "read"):
                    file_obj.seek(0)
                    shutil.copyfileobj(file_obj, buffer)
                else:
                    buffer.write(file_obj)
            
            storage_key = f"{folder}/{unique_filename}"
            url = self.get_url(storage_key)
            return url, storage_key
        except Exception as e:
            raise StorageException(f"Failed to upload file to local storage: {str(e)}")

    async def get_file_bytes(self, storage_key: str) -> bytes:
        try:
            file_path = os.path.join(self.base_dir, storage_key)
            if not os.path.exists(file_path):
                raise StorageException(f"File not found for key: {storage_key}")
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            raise StorageException(f"Failed to read file: {str(e)}")

    async def delete_file(self, storage_key: str) -> bool:
        try:
            file_path = os.path.join(self.base_dir, storage_key)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            raise StorageException(f"Failed to delete file: {str(e)}")

    def get_url(self, storage_key: str) -> str:
        # Standard relative API endpoint for serving uploads
        return f"{settings.API_V1_PREFIX}/storage/{storage_key}"

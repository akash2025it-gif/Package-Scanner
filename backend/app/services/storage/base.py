from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Tuple


class StorageService(ABC):
    """Abstract interface for object storage (Local, MinIO, S3)."""

    @abstractmethod
    async def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "uploads",
    ) -> Tuple[str, str]:
        """
        Uploads a file object to storage.
        Returns a tuple: (public_or_accessible_url, storage_key)
        """
        pass

    @abstractmethod
    async def get_file_bytes(self, storage_key: str) -> bytes:
        """Retrieves raw bytes of a file by its storage key."""
        pass

    @abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        """Deletes a file by its storage key."""
        pass

    @abstractmethod
    def get_url(self, storage_key: str) -> str:
        """Generates an accessible URL for a given storage key."""
        pass

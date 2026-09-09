import io
import os
import uuid
from typing import BinaryIO, Tuple
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.exceptions import StorageException
from app.services.storage.base import StorageService


class S3StorageService(StorageService):
    """S3 & MinIO compatible object storage implementation."""

    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        session_kwargs = {
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
            "region_name": settings.S3_REGION,
        }
        if settings.S3_ENDPOINT_URL:
            session_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

        self.s3_client = boto3.client("s3", **session_kwargs)

    async def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "uploads",
    ) -> Tuple[str, str]:
        try:
            ext = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            storage_key = f"{folder}/{unique_filename}"
            
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                storage_key,
                ExtraArgs={"ContentType": content_type},
            )
            
            url = self.get_url(storage_key)
            return url, storage_key
        except ClientError as e:
            raise StorageException(f"S3 Upload failed: {str(e)}")

    async def get_file_bytes(self, storage_key: str) -> bytes:
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=storage_key)
            return response["Body"].read()
        except ClientError as e:
            raise StorageException(f"S3 Download failed: {str(e)}")

    async def delete_file(self, storage_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except ClientError as e:
            raise StorageException(f"S3 Delete failed: {str(e)}")

    def get_url(self, storage_key: str) -> str:
        if settings.S3_ENDPOINT_URL:
            return f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{storage_key}"
        return f"https://{self.bucket_name}.s3.{settings.S3_REGION}.amazonaws.com/{storage_key}"

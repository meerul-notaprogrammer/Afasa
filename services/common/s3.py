"""
AFASA 2.0 - MinIO/S3 Storage Client
Tenant-isolated object storage
"""
from typing import Optional
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
import io

from .settings import get_settings


class StorageClient:
    def __init__(self):
        settings = get_settings()
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self._bucket = settings.minio_bucket
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
        except S3Error as e:
            print(f"Bucket check error: {e}")
    
    def _tenant_key(self, tenant_id: str, path: str) -> str:
        """Generate tenant-isolated key"""
        return f"tenant/{tenant_id}/{path}"
    
    def upload_snapshot(
        self,
        tenant_id: str,
        snapshot_id: str,
        data: bytes,
        content_type: str = "image/jpeg"
    ) -> str:
        """Upload a snapshot image"""
        key = self._tenant_key(tenant_id, f"snapshots/{snapshot_id}.jpg")
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type
        )
        return key
    
    def upload_annotated(
        self,
        tenant_id: str,
        snapshot_id: str,
        data: bytes,
        content_type: str = "image/jpeg"
    ) -> str:
        """Upload an annotated image"""
        key = self._tenant_key(tenant_id, f"annotated/{snapshot_id}.jpg")
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type
        )
        return key
    
    def upload_report(
        self,
        tenant_id: str,
        report_id: str,
        data: bytes,
        format: str = "pdf"
    ) -> str:
        """Upload a report"""
        key = self._tenant_key(tenant_id, f"reports/{report_id}.{format}")
        content_type = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type
        )
        return key
    
    def get_object(self, key: str) -> bytes:
        """Get object data"""
        response = self._client.get_object(self._bucket, key)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    
    def get_presigned_url(
        self,
        key: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate a presigned URL for download"""
        return self._client.presigned_get_object(
            self._bucket,
            key,
            expires=expires
        )
    
    def delete_object(self, key: str):
        """Delete an object"""
        self._client.remove_object(self._bucket, key)
    
    def list_objects(self, prefix: str) -> list[str]:
        """List objects with a prefix"""
        objects = self._client.list_objects(self._bucket, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]


_storage_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client

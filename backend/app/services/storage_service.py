"""
SupportPilot AI — Storage Service
Pluggable file-storage backend: local disk (dev) or Google Cloud Storage (GCP production).

Usage:
    Set STORAGE_BACKEND=gcs and GCS_BUCKET_NAME=<bucket> + GOOGLE_APPLICATION_CREDENTIALS=/path/key.json
    to route all uploads through GCS automatically.
    Default STORAGE_BACKEND=local uses the existing upload_dir behaviour.
"""

import io
import os
from pathlib import Path
from typing import BinaryIO

from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Storage backend selection
_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()
_GCS_BUCKET = os.getenv("GCS_BUCKET_NAME", "")
_GCS_PROJECT = os.getenv("GCS_PROJECT_ID", "")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class StorageBackend:
    async def upload(self, org_id: str, filename: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        """Store file and return the canonical storage path / URI."""
        raise NotImplementedError

    async def download(self, storage_path: str) -> bytes:
        """Return raw file bytes for a given storage_path."""
        raise NotImplementedError

    async def delete(self, storage_path: str) -> None:
        """Delete the file at storage_path."""
        raise NotImplementedError

    def exists(self, storage_path: str) -> bool:
        """Return True if the file at storage_path exists."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Local disk backend (development / fallback)
# ---------------------------------------------------------------------------

class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    async def upload(self, org_id: str, filename: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        dest_dir = self.base_dir / org_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename
        content = data.read()
        dest_path.write_bytes(content)
        logger.info("storage_local_upload", path=str(dest_path), org_id=org_id)
        return str(dest_path)

    async def download(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    async def delete(self, storage_path: str) -> None:
        p = Path(storage_path)
        if p.exists():
            p.unlink()
            logger.info("storage_local_delete", path=storage_path)

    def exists(self, storage_path: str) -> bool:
        return Path(storage_path).exists()


# ---------------------------------------------------------------------------
# Google Cloud Storage backend
# ---------------------------------------------------------------------------

class GCSStorageBackend(StorageBackend):
    """
    Uses google-cloud-storage SDK.
    Authentication via GOOGLE_APPLICATION_CREDENTIALS env var (service account JSON key),
    or Workload Identity when running inside GCP with appropriate IAM bindings.
    """

    def __init__(self, bucket_name: str, project_id: str = ""):
        # Lazy import — avoids import error on dev machines without GCS SDK installed
        try:
            from google.cloud import storage as gcs_lib  # noqa: PLC0415
            self._gcs = gcs_lib
        except ImportError as exc:
            raise RuntimeError(
                "google-cloud-storage is not installed. Run: pip install google-cloud-storage"
            ) from exc

        self.bucket_name = bucket_name
        self.project_id = project_id
        self._client = None  # created lazily to avoid blocking at import

    def _get_client(self):
        if self._client is None:
            self._client = self._gcs.Client(project=self.project_id or None)
        return self._client

    def _get_bucket(self):
        return self._get_client().bucket(self.bucket_name)

    def _blob_name(self, org_id: str, filename: str) -> str:
        return f"uploads/{org_id}/{filename}"

    async def upload(self, org_id: str, filename: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        blob_name = self._blob_name(org_id, filename)
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)

        content = data.read()
        blob.upload_from_string(content, content_type=content_type)
        gcs_uri = f"gs://{self.bucket_name}/{blob_name}"
        logger.info("storage_gcs_upload", uri=gcs_uri, org_id=org_id)
        return gcs_uri

    async def download(self, storage_path: str) -> bytes:
        # storage_path may be a GCS URI (gs://bucket/path) or bare blob name
        if storage_path.startswith("gs://"):
            parts = storage_path[5:].split("/", 1)
            bucket_name = parts[0]
            blob_name = parts[1] if len(parts) > 1 else ""
            bucket = self._get_client().bucket(bucket_name)
        else:
            blob_name = storage_path
            bucket = self._get_bucket()

        blob = bucket.blob(blob_name)
        content = blob.download_as_bytes()
        return content

    async def delete(self, storage_path: str) -> None:
        if storage_path.startswith("gs://"):
            parts = storage_path[5:].split("/", 1)
            bucket_name = parts[0]
            blob_name = parts[1] if len(parts) > 1 else ""
            bucket = self._get_client().bucket(bucket_name)
        else:
            blob_name = storage_path
            bucket = self._get_bucket()

        blob = bucket.blob(blob_name)
        try:
            blob.delete()
            logger.info("storage_gcs_delete", path=storage_path)
        except Exception as exc:
            logger.warning("storage_gcs_delete_failed", path=storage_path, error=str(exc))

    def exists(self, storage_path: str) -> bool:
        if storage_path.startswith("gs://"):
            parts = storage_path[5:].split("/", 1)
            bucket_name = parts[0]
            blob_name = parts[1] if len(parts) > 1 else ""
            bucket = self._get_client().bucket(bucket_name)
        else:
            blob_name = storage_path
            bucket = self._get_bucket()
        return bucket.blob(blob_name).exists()

    def get_signed_url(self, storage_path: str, expiration_minutes: int = 60) -> str:
        """Generate a temporary signed URL for direct browser download."""
        import datetime  # noqa: PLC0415
        blob_name = storage_path
        if storage_path.startswith("gs://"):
            blob_name = storage_path[5:].split("/", 1)[1]
        blob = self._get_bucket().blob(blob_name)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method="GET",
        )
        return url


# ---------------------------------------------------------------------------
# Factory — select backend at module load time
# ---------------------------------------------------------------------------

def get_storage_backend() -> StorageBackend:
    if _BACKEND == "gcs":
        if not _GCS_BUCKET:
            raise RuntimeError("STORAGE_BACKEND=gcs requires GCS_BUCKET_NAME to be set.")
        logger.info("storage_backend_gcs", bucket=_GCS_BUCKET)
        return GCSStorageBackend(bucket_name=_GCS_BUCKET, project_id=_GCS_PROJECT)

    logger.info("storage_backend_local", base_dir=settings.upload_dir)
    return LocalStorageBackend(base_dir=settings.upload_dir)


# Singleton
_storage_backend: StorageBackend | None = None


def storage() -> StorageBackend:
    global _storage_backend
    if _storage_backend is None:
        _storage_backend = get_storage_backend()
    return _storage_backend

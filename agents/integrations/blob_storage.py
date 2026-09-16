"""Cloud Blob Storage abstraction with seamless Azure Blob Storage and local fallback."""

import logging
import os
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger("leadops.blob_storage")

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    HAS_AZURE_STORAGE = True
except ImportError:
    HAS_AZURE_STORAGE = False


class BlobStorageManager:
    """Manages unstructured cloud artifacts, DOM dumps, and crawler payloads."""

    def __init__(
        self,
        connection_string: str | None = None,
        default_container: str = "artifacts",
        local_dir: str = "build_artifacts",
    ) -> None:
        self.conn_str = connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        self.default_container = default_container
        self.local_dir = Path(local_dir)
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self.client: BlobServiceClient | None = None

        if self.conn_str and HAS_AZURE_STORAGE:
            try:
                self.client = BlobServiceClient.from_connection_string(self.conn_str)
                # Ensure default container exists
                container_client = self.client.get_container_client(self.default_container)
                if not container_client.exists():
                    container_client.create_container()
                logger.info("Azure Blob Storage connected: container='%s'", self.default_container)
            except Exception as e:
                logger.warning("Failed to initialize Azure Blob Storage (%s), falling back to local disk", e)
                self.client = None

    @property
    def is_cloud_enabled(self) -> bool:
        return self.client is not None

    def upload_bytes(
        self,
        data: bytes,
        blob_path: str,
        container: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload raw bytes to Azure Blob Storage or local disk."""
        target_container = container or self.default_container
        normalized_path = blob_path.replace("\\", "/").lstrip("/")

        if self.client:
            try:
                blob_client = self.client.get_blob_client(
                    container=target_container,
                    blob=normalized_path,
                )
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type) if ContentSettings else None,
                )
                logger.debug("Uploaded %d bytes to azure blob: %s/%s", len(data), target_container, normalized_path)
                return blob_client.url
            except Exception as e:
                logger.warning("Azure blob upload failed (%s), writing locally", e)

        # Local fallback
        dest = self.local_dir / normalized_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest)

    def upload_text(
        self,
        text: str,
        blob_path: str,
        container: str | None = None,
        content_type: str = "text/plain; charset=utf-8",
    ) -> str:
        """Upload text content to Azure Blob Storage or local disk."""
        return self.upload_bytes(
            text.encode("utf-8"),
            blob_path=blob_path,
            container=container,
            content_type=content_type,
        )

    def upload_file(
        self,
        local_file: Path | str,
        blob_path: str,
        container: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a physical local file to blob storage."""
        path = Path(local_file)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {path}")
        return self.upload_bytes(
            path.read_bytes(),
            blob_path=blob_path,
            container=container,
            content_type=content_type,
        )

    def download_bytes(self, blob_path: str, container: str | None = None) -> bytes:
        """Download raw bytes from Azure Blob Storage or local disk."""
        target_container = container or self.default_container
        normalized_path = blob_path.replace("\\", "/").lstrip("/")

        if self.client:
            try:
                blob_client = self.client.get_blob_client(
                    container=target_container,
                    blob=normalized_path,
                )
                return blob_client.download_blob().readall()
            except Exception as e:
                logger.warning("Azure blob download failed (%s), reading locally", e)

        dest = self.local_dir / normalized_path
        if not dest.exists():
            raise FileNotFoundError(f"Artifact not found locally or in blob: {normalized_path}")
        return dest.read_bytes()

    def download_text(self, blob_path: str, container: str | None = None) -> str:
        """Download text content from Azure Blob Storage or local disk."""
        return self.download_bytes(blob_path, container).decode("utf-8")

    def exists(self, blob_path: str, container: str | None = None) -> bool:
        """Check if a blob exists in storage or on local disk."""
        target_container = container or self.default_container
        normalized_path = blob_path.replace("\\", "/").lstrip("/")

        if self.client:
            try:
                blob_client = self.client.get_blob_client(container=target_container, blob=normalized_path)
                return bool(blob_client.exists())
            except Exception as ex:
                logger.debug(f"Azure blob exists check fallback to local for {normalized_path}: {ex}")

        dest = self.local_dir / normalized_path
        return dest.exists()


# Global singleton instance
blob_storage = BlobStorageManager()

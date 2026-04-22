"""Object storage adapter stubs for platform artifacts."""

from urllib.parse import urlparse

from doc_platform_contracts.storage_keys import ArtifactType, build_storage_key

from api_service.config import APISettings, get_settings


class StorageAdapter:
    def __init__(self, settings: APISettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.endpoint = self.settings.object_storage_endpoint.rstrip("/")
        self.bucket = self.settings.object_storage_bucket
        self.access_key = self.settings.object_storage_access_key
        self.secret_key = self.settings.object_storage_secret_key

    def build_storage_key(
        self,
        *,
        tenant_id: str,
        job_id: str,
        stage: str,
        artifact_type: ArtifactType,
        filename: str,
    ) -> str:
        return build_storage_key(
            tenant_id=tenant_id,
            job_id=job_id,
            stage=stage,
            artifact_type=artifact_type,
            filename=filename,
        )

    def put_artifact(self, *, storage_key: str, content: bytes) -> dict[str, str | int]:
        return {
            "bucket": self.bucket,
            "storage_key": storage_key,
            "bytes_written": len(content),
        }

    def get_artifact_uri(self, storage_key: str) -> str:
        parsed = urlparse(self.endpoint)
        base = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else self.endpoint
        return f"{base}/{self.bucket}/{storage_key}"

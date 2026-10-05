from pathlib import Path
from urllib.parse import quote
import boto3
from app.core.config import settings

class ArtifactStorage:
    def __init__(self):
        self.backend = settings.storage_backend.lower()
        if self.backend == "s3":
            if not settings.s3_bucket:
                raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
            self.client = boto3.client("s3", region_name=settings.s3_region, endpoint_url=settings.s3_endpoint_url or None)

    def save(self, local_path: str, key: str) -> str:
        if self.backend == "s3":
            self.client.upload_file(local_path, settings.s3_bucket, key, ExtraArgs={"ContentType": self._content_type(local_path)})
            return key
        return str(Path(local_path).resolve())

    def presigned_url(self, key_or_path: str) -> str | None:
        if self.backend == "s3":
            return self.client.generate_presigned_url("get_object", Params={"Bucket": settings.s3_bucket, "Key": key_or_path}, ExpiresIn=settings.s3_presign_seconds)
        return None

    @staticmethod
    def _content_type(path: str) -> str:
        return {".pdf":"application/pdf", ".docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}.get(Path(path).suffix.lower(), "application/octet-stream")

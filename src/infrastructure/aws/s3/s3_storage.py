import json
from typing import Any

from botocore.exceptions import ClientError

from src.application.ports.output.storage_port import StoragePort
from src.domain.errors.domain_errors import TransientError, ValidationError


class S3Storage(StoragePort):
    def __init__(self, s3_client):
        self._s3 = s3_client

    def get_json(self, bucket: str, key: str) -> dict[str, Any]:
        payload = self.get_text(bucket, key)
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValidationError("Invalid JSON in S3 object") from exc
        if not isinstance(parsed, dict):
            raise ValidationError("Expected JSON object in S3 object")
        return parsed

    def get_text(self, bucket: str, key: str) -> str:
        try:
            response = self._s3.get_object(Bucket=bucket, Key=key)
            body = response["Body"].read()
            return body.decode("utf-8")
        except ClientError as exc:
            raise TransientError(f"Failed to fetch S3 object {bucket}/{key}: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise ValidationError("S3 object is not valid UTF-8 text") from exc

    def put_bytes(self, bucket: str, key: str, content: bytes, content_type: str) -> None:
        try:
            self._s3.put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
        except ClientError as exc:
            raise TransientError(f"Failed to upload S3 object {bucket}/{key}: {exc}") from exc

    def put_json(self, bucket: str, key: str, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.put_bytes(bucket, key, body, "application/json")

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise TransientError(f"Failed to check S3 object {bucket}/{key}: {exc}") from exc

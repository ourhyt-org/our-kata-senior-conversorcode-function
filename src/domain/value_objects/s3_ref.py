from dataclasses import dataclass

from src.domain.errors.domain_errors import ValidationError


@dataclass(frozen=True)
class S3ObjectRef:
    bucket: str
    key: str

    def __post_init__(self):
        if not self.bucket or not self.bucket.strip():
            raise ValidationError("S3 bucket is required")
        if not self.key or not self.key.strip():
            raise ValidationError("S3 key is required")

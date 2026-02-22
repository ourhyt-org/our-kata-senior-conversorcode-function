from uuid import UUID

from src.domain.errors.domain_errors import ValidationError


class JobId:
    def __init__(self, value: str):
        if not value or not value.strip():
            raise ValidationError("jobId is required")
        try:
            UUID(value)
        except ValueError as exc:
            raise ValidationError("jobId must be a valid UUID") from exc
        self.value = value

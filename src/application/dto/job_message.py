from dataclasses import dataclass

from src.domain.errors.domain_errors import ValidationError
from src.domain.value_objects.job_id import JobId
from src.domain.value_objects.s3_ref import S3ObjectRef


@dataclass(frozen=True)
class McpConfig:
    base_url: str | None
    tool: str | None


@dataclass(frozen=True)
class JobMessage:
    job_id: str
    request: S3ObjectRef
    code: S3ObjectRef
    mcp: McpConfig

    @staticmethod
    def from_dict(data: dict) -> "JobMessage":
        if not isinstance(data, dict):
            raise ValidationError("SQS body must be an object")
        job_id = str(data.get("jobId", ""))
        JobId(job_id)
        request = S3ObjectRef(
            bucket=str(data.get("requestS3Bucket", "")),
            key=str(data.get("requestS3Key", "")),
        )
        code = S3ObjectRef(
            bucket=str(data.get("codeS3Bucket", "")),
            key=str(data.get("codeS3Key", "")),
        )
        mcp_data = data.get("mcp") or {}
        if not isinstance(mcp_data, dict):
            raise ValidationError("mcp must be an object")
        base_url = mcp_data.get("baseUrl")
        tool = mcp_data.get("tool")
        return JobMessage(
            job_id=job_id,
            request=request,
            code=code,
            mcp=McpConfig(
                base_url=str(base_url) if base_url else None,
                tool=str(tool) if tool else None,
            ),
        )

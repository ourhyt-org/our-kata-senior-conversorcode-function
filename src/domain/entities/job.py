from dataclasses import dataclass
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    status: JobStatus
    started_at: str | None = None
    finished_at: str | None = None
    output_s3_key: str | None = None
    report_s3_key: str | None = None
    error_message: str | None = None
    ttl: int | None = None

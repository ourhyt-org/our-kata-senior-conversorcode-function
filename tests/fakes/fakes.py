from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.dto.conversion_request import ConversionRequest
from src.application.ports.output.clock_port import ClockPort
from src.application.ports.output.job_repository_port import JobRepositoryPort
from src.application.ports.output.logger_port import LoggerPort
from src.application.ports.output.mcp_client_port import McpClientPort
from src.application.ports.output.storage_port import StoragePort
from src.domain.entities.job import JobRecord
from src.domain.entities.mcp_result import McpResult


class FakeClock(ClockPort):
    def __init__(self, now: datetime | None = None):
        self._now = now or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now_utc(self) -> datetime:
        return self._now


class FakeLogger(LoggerPort):
    def __init__(self, context: dict | None = None):
        self.context = context or {}
        self.messages: list[tuple[str, str, dict]] = []

    def with_context(self, **kwargs):
        merged = dict(self.context)
        merged.update(kwargs)
        return FakeLogger(merged)

    def info(self, message: str, **kwargs):
        self.messages.append(("INFO", message, kwargs))

    def warning(self, message: str, **kwargs):
        self.messages.append(("WARNING", message, kwargs))

    def error(self, message: str, **kwargs):
        self.messages.append(("ERROR", message, kwargs))


class FakeJobRepository(JobRepositoryPort):
    def __init__(self, job: JobRecord | None):
        self.job = job
        self.mark_running_calls = 0
        self.mark_finished_calls = 0
        self.mark_failed_calls = 0

    def get_job(self, job_id: str):
        return self.job

    def mark_running(self, job_id: str, started_at_iso: str, stale_before_iso: str):
        self.mark_running_calls += 1
        return True

    def mark_finished(self, job_id: str, finished_at_iso: str, output_s3_key: str, report_s3_key: str):
        self.mark_finished_calls += 1

    def mark_failed(self, job_id: str, finished_at_iso: str, error_message: str):
        self.mark_failed_calls += 1


class FakeStorage(StoragePort):
    def __init__(self):
        self.exists_map: dict[tuple[str, str], bool] = {}
        self.json_map: dict[tuple[str, str], dict] = {}
        self.text_map: dict[tuple[str, str], str] = {}
        self.put_bytes_calls = 0
        self.put_json_calls = 0

    def get_json(self, bucket: str, key: str):
        return self.json_map[(bucket, key)]

    def get_text(self, bucket: str, key: str):
        return self.text_map[(bucket, key)]

    def put_bytes(self, bucket: str, key: str, content: bytes, content_type: str):
        self.put_bytes_calls += 1

    def put_json(self, bucket: str, key: str, payload: dict):
        self.put_json_calls += 1

    def exists(self, bucket: str, key: str):
        return self.exists_map.get((bucket, key), False)


@dataclass
class FakeMcpClient(McpClientPort):
    result: McpResult | None = None
    calls: int = 0

    def convert(self, base_url: str, tool: str | None, request: ConversionRequest, code: str) -> McpResult:
        self.calls += 1
        if self.result is None:
            raise RuntimeError("No fake result configured")
        return self.result

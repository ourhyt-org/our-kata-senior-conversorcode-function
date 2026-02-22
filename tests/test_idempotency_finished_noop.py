from datetime import datetime, timezone

from src.application.dto.job_message import JobMessage, McpConfig
from src.application.use_cases.process_conversion_job import ProcessConversionJobUseCase
from src.domain.entities.job import JobRecord, JobStatus
from tests.fakes.fakes import FakeClock, FakeJobRepository, FakeLogger, FakeMcpClient, FakeStorage


def test_finished_job_is_noop():
    job = JobRecord(
        job_id="20e28f8e-4220-433b-9ef9-744720f31020",
        status=JobStatus.FINISHED,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
    )
    repo = FakeJobRepository(job)
    storage = FakeStorage()
    mcp = FakeMcpClient()
    use_case = ProcessConversionJobUseCase(
        job_repository=repo,
        storage=storage,
        mcp_client=mcp,
        clock=FakeClock(),
        logger=FakeLogger(),
        output_bucket="out",
        fallback_mcp_base_url="https://mcp.local/convert",
        max_files=200,
        max_zip_mb=50,
        stale_running_minutes=20,
    )
    message = JobMessage.from_dict(
        {
            "jobId": "20e28f8e-4220-433b-9ef9-744720f31020",
            "requestS3Bucket": "in",
            "requestS3Key": "conversions/20e28f8e-4220-433b-9ef9-744720f31020/request.json",
            "codeS3Bucket": "in",
            "codeS3Key": "conversions/20e28f8e-4220-433b-9ef9-744720f31020/input.cob",
            "mcp": {"baseUrl": "https://mcp.local/convert"},
        }
    )

    result = use_case.execute(message)

    assert result.success is True
    assert result.no_op is True
    assert repo.mark_running_calls == 0
    assert mcp.calls == 0
    assert storage.put_bytes_calls == 0
    assert storage.put_json_calls == 0

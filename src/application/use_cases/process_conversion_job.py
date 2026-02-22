import hashlib
from datetime import timedelta

from src.application.dto.conversion_request import ConversionRequest
from src.application.dto.job_message import JobMessage
from src.application.dto.process_result import ProcessResult
from src.application.ports.input.process_job_use_case import ProcessJobUseCase
from src.application.ports.output.clock_port import ClockPort
from src.application.ports.output.job_repository_port import JobRepositoryPort
from src.application.ports.output.logger_port import LoggerPort
from src.application.ports.output.mcp_client_port import McpClientPort
from src.application.ports.output.storage_port import StoragePort
from src.domain.entities.job import JobStatus
from src.domain.errors.domain_errors import DomainError, McpBusinessError, TransientError, ValidationError
from src.infrastructure.packaging.zip_packager import build_outputs


class ProcessConversionJobUseCase(ProcessJobUseCase):
    def __init__(
        self,
        job_repository: JobRepositoryPort,
        storage: StoragePort,
        mcp_client: McpClientPort,
        clock: ClockPort,
        logger: LoggerPort,
        output_bucket: str,
        fallback_mcp_base_url: str | None,
        max_files: int,
        max_zip_mb: int,
        stale_running_minutes: int,
    ):
        self._job_repository = job_repository
        self._storage = storage
        self._mcp_client = mcp_client
        self._clock = clock
        self._logger = logger
        self._output_bucket = output_bucket
        self._fallback_mcp_base_url = fallback_mcp_base_url
        self._max_files = max_files
        self._max_zip_mb = max_zip_mb
        self._stale_running_minutes = stale_running_minutes

    def execute(self, message: JobMessage) -> ProcessResult:
        logger = self._logger.with_context(correlationId=message.job_id, jobId=message.job_id)
        logger.info("job_processing_started", eventType="job_start")
        now = self._clock.now_utc()
        now_iso = now.isoformat()
        stale_before_iso = (now - timedelta(minutes=self._stale_running_minutes)).isoformat()
        output_key = f"conversions/{message.job_id}/output.zip"
        report_key = f"conversions/{message.job_id}/report.json"

        try:
            job = self._job_repository.get_job(message.job_id)
            if job is None:
                return self._fail_non_retryable(message.job_id, now_iso, "Job not found", logger)

            if job.status == JobStatus.FINISHED:
                logger.info("job_already_finished", eventType="idempotency")
                return ProcessResult(success=True, retriable=False, no_op=True, message="already finished")

            if job.status == JobStatus.RUNNING and job.started_at and job.started_at > stale_before_iso:
                logger.info("job_recent_running_skip", eventType="idempotency")
                return ProcessResult(success=True, retriable=False, no_op=True, message="currently running")

            if not self._job_repository.mark_running(message.job_id, now_iso, stale_before_iso):
                logger.info("job_running_lock_not_acquired", eventType="idempotency")
                return ProcessResult(success=True, retriable=False, no_op=True, message="lock not acquired")

            if self._storage.exists(self._output_bucket, output_key) and self._storage.exists(self._output_bucket, report_key):
                self._job_repository.mark_finished(message.job_id, now_iso, output_key, report_key)
                logger.info("job_recovered_from_existing_artifacts", eventType="recovery")
                return ProcessResult(success=True, retriable=False, no_op=False, message="recovered")

            request_payload = self._storage.get_json(message.request.bucket, message.request.key)
            conversion_request = ConversionRequest.from_dict(request_payload)
            code = self._storage.get_text(message.code.bucket, message.code.key)

            code_bytes = code.encode("utf-8")
            code_hash = hashlib.sha256(code_bytes).hexdigest()
            logger.info(
                "source_loaded",
                eventType="source_loaded",
                sourceSizeBytes=len(code_bytes),
                sourceSha256=code_hash,
            )

            base_url = message.mcp.base_url or self._fallback_mcp_base_url
            if not base_url:
                raise ValidationError("MCP base URL is missing")

            mcp_result = self._mcp_client.convert(base_url, message.mcp.tool, conversion_request, code)
            if mcp_result.status == "error":
                raise McpBusinessError(mcp_result.summary or "MCP returned status=error")

            output_zip, report_json = build_outputs(
                files=mcp_result.files,
                status=mcp_result.status,
                summary=mcp_result.summary,
                warnings=mcp_result.warnings,
                report=mcp_result.report,
                max_files=self._max_files,
                max_zip_mb=self._max_zip_mb,
            )

            self._storage.put_bytes(self._output_bucket, output_key, output_zip, "application/zip")
            self._storage.put_json(self._output_bucket, report_key, report_json)

            finish_iso = self._clock.now_utc().isoformat()
            self._job_repository.mark_finished(message.job_id, finish_iso, output_key, report_key)
            logger.info("job_processing_finished", eventType="job_finish", outputS3Key=output_key, reportS3Key=report_key)
            return ProcessResult(success=True, retriable=False)
        except (ValidationError, McpBusinessError) as exc:
            return self._fail_non_retryable(message.job_id, self._clock.now_utc().isoformat(), str(exc), logger)
        except DomainError as exc:
            logger.error("job_domain_error", eventType="job_error", error=str(exc))
            return ProcessResult(success=False, retriable=True, no_op=False, message=str(exc))
        except Exception as exc:
            logger.error("job_unexpected_error", eventType="job_error", error=str(exc))
            return ProcessResult(success=False, retriable=True, no_op=False, message="unexpected error")

    def _fail_non_retryable(self, job_id: str, finished_at_iso: str, message: str, logger: LoggerPort) -> ProcessResult:
        try:
            self._job_repository.mark_failed(job_id, finished_at_iso, message)
        except TransientError:
            logger.error("job_mark_failed_transient_error", eventType="job_error", error=message)
            return ProcessResult(success=False, retriable=True, no_op=False, message=message)
        logger.error("job_failed", eventType="job_failed", error=message)
        return ProcessResult(success=True, retriable=False, no_op=False, message=message)

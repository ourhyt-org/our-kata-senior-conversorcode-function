from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.dto.process_result import ProcessResult
from src.application.use_cases.process_conversion_job import ProcessConversionJobUseCase
from src.infrastructure.aws.dynamodb.job_repository import DynamoJobRepository
from src.infrastructure.aws.factories import build_dynamodb_resource, build_s3_client
from src.infrastructure.aws.s3.s3_storage import S3Storage
from src.infrastructure.aws.sqs.event_parser import parse_sqs_record
from src.infrastructure.config.settings import Settings, load_settings
from src.infrastructure.http.mcp_client.mock_mcp_client import MockMcpClient
from src.infrastructure.logging.json_logger import build_logger


class UtcClock:
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Container:
    settings: Settings
    use_case: ProcessConversionJobUseCase


_CONTAINER: Container | None = None


def _build_container() -> Container:
    settings = load_settings()
    logger = build_logger("function_b", settings.log_level)
    ddb = build_dynamodb_resource()
    s3 = build_s3_client()
    repository = DynamoJobRepository(ddb, settings.ddb_table)
    storage = S3Storage(s3)
    if settings.mcp_use_mock:
        mcp_client = MockMcpClient(mode=settings.mcp_mock_mode)
    else:
        from src.infrastructure.http.mcp_client.httpx_mcp_client import HttpxMcpClient

        mcp_client = HttpxMcpClient()
    use_case = ProcessConversionJobUseCase(
        job_repository=repository,
        storage=storage,
        mcp_client=mcp_client,
        clock=UtcClock(),
        logger=logger,
        output_bucket=settings.output_bucket,
        fallback_mcp_base_url=settings.mcp_base_url,
        max_files=settings.max_files,
        max_zip_mb=settings.max_zip_mb,
        stale_running_minutes=settings.stale_running_minutes,
    )
    return Container(settings=settings, use_case=use_case)


def _get_container() -> Container:
    global _CONTAINER
    if _CONTAINER is None:
        _CONTAINER = _build_container()
    return _CONTAINER


def lambda_handler(event, context):
    container = _get_container()
    failures: list[dict[str, str]] = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        try:
            message = parse_sqs_record(record)
            result: ProcessResult = container.use_case.execute(message)
            if not result.success and result.retriable:
                failures.append({"itemIdentifier": message_id})
        except Exception:
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}

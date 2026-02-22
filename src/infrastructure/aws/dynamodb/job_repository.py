from botocore.exceptions import ClientError

from src.application.ports.output.job_repository_port import JobRepositoryPort
from src.domain.entities.job import JobRecord, JobStatus
from src.domain.errors.domain_errors import TransientError


class DynamoJobRepository(JobRepositoryPort):
    def __init__(self, dynamodb_resource, table_name: str):
        self._table = dynamodb_resource.Table(table_name)

    def get_job(self, job_id: str) -> JobRecord | None:
        try:
            response = self._table.get_item(Key={"jobId": job_id})
            item = response.get("Item")
            if not item:
                return None
            status_value = str(item.get("status", "PENDING"))
            try:
                status = JobStatus(status_value)
            except ValueError:
                status = JobStatus.PENDING
            return JobRecord(
                job_id=str(item.get("jobId", job_id)),
                status=status,
                started_at=item.get("startedAt"),
                finished_at=item.get("finishedAt"),
                output_s3_key=item.get("outputS3Key"),
                report_s3_key=item.get("reportS3Key"),
                error_message=item.get("errorMessage"),
                ttl=item.get("ttl"),
            )
        except ClientError as exc:
            raise TransientError(f"Failed to get job: {exc}") from exc

    def mark_running(self, job_id: str, started_at_iso: str, stale_before_iso: str) -> bool:
        try:
            self._table.update_item(
                Key={"jobId": job_id},
                UpdateExpression="SET #status = :running, #startedAt = :startedAt REMOVE #errorMessage",
                ConditionExpression=(
                    "attribute_exists(jobId) AND ("
                    "#status IN (:pending, :failed) OR "
                    "(#status = :running AND #startedAt < :staleBefore)"
                    ")"
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                    "#startedAt": "startedAt",
                    "#errorMessage": "errorMessage",
                },
                ExpressionAttributeValues={
                    ":running": JobStatus.RUNNING.value,
                    ":pending": JobStatus.PENDING.value,
                    ":failed": JobStatus.FAILED.value,
                    ":startedAt": started_at_iso,
                    ":staleBefore": stale_before_iso,
                },
            )
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise TransientError(f"Failed to mark running: {exc}") from exc

    def mark_finished(self, job_id: str, finished_at_iso: str, output_s3_key: str, report_s3_key: str) -> None:
        try:
            self._table.update_item(
                Key={"jobId": job_id},
                UpdateExpression=(
                    "SET #status = :finished, #finishedAt = :finishedAt, "
                    "#outputS3Key = :outputS3Key, #reportS3Key = :reportS3Key REMOVE #errorMessage"
                ),
                ConditionExpression="attribute_exists(jobId)",
                ExpressionAttributeNames={
                    "#status": "status",
                    "#finishedAt": "finishedAt",
                    "#outputS3Key": "outputS3Key",
                    "#reportS3Key": "reportS3Key",
                    "#errorMessage": "errorMessage",
                },
                ExpressionAttributeValues={
                    ":finished": JobStatus.FINISHED.value,
                    ":finishedAt": finished_at_iso,
                    ":outputS3Key": output_s3_key,
                    ":reportS3Key": report_s3_key,
                },
            )
        except ClientError as exc:
            raise TransientError(f"Failed to mark finished: {exc}") from exc

    def mark_failed(self, job_id: str, finished_at_iso: str, error_message: str) -> None:
        try:
            self._table.update_item(
                Key={"jobId": job_id},
                UpdateExpression="SET #status = :failed, #finishedAt = :finishedAt, #errorMessage = :errorMessage",
                ConditionExpression="attribute_exists(jobId)",
                ExpressionAttributeNames={
                    "#status": "status",
                    "#finishedAt": "finishedAt",
                    "#errorMessage": "errorMessage",
                },
                ExpressionAttributeValues={
                    ":failed": JobStatus.FAILED.value,
                    ":finishedAt": finished_at_iso,
                    ":errorMessage": error_message[:2000],
                },
            )
        except ClientError as exc:
            raise TransientError(f"Failed to mark failed: {exc}") from exc

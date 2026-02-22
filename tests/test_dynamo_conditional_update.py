from botocore.exceptions import ClientError

from src.domain.errors.domain_errors import TransientError
from src.infrastructure.aws.dynamodb.job_repository import DynamoJobRepository


class FakeTable:
    def __init__(self, exc=None):
        self.exc = exc
        self.calls = 0

    def get_item(self, Key):
        return {"Item": {"jobId": Key["jobId"], "status": "PENDING"}}

    def update_item(self, **kwargs):
        self.calls += 1
        if self.exc:
            raise self.exc
        return {}


class FakeDynamoResource:
    def __init__(self, table):
        self._table = table

    def Table(self, name):
        return self._table


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "UpdateItem")


def test_mark_running_returns_false_on_conditional_check_failed():
    table = FakeTable(exc=_client_error("ConditionalCheckFailedException"))
    repo = DynamoJobRepository(FakeDynamoResource(table), "jobs")

    result = repo.mark_running(
        job_id="87f6b377-c008-42be-8bd2-d164978fcb77",
        started_at_iso="2026-01-01T00:00:00+00:00",
        stale_before_iso="2025-12-31T23:40:00+00:00",
    )

    assert result is False


def test_mark_running_raises_transient_on_non_conditional_error():
    table = FakeTable(exc=_client_error("ProvisionedThroughputExceededException"))
    repo = DynamoJobRepository(FakeDynamoResource(table), "jobs")

    try:
        repo.mark_running(
            job_id="87f6b377-c008-42be-8bd2-d164978fcb77",
            started_at_iso="2026-01-01T00:00:00+00:00",
            stale_before_iso="2025-12-31T23:40:00+00:00",
        )
        assert False
    except TransientError:
        assert True

import json

from src.application.dto.job_message import JobMessage
from src.domain.errors.domain_errors import ValidationError


def parse_sqs_record(record: dict) -> JobMessage:
    body = record.get("body")
    if body is None:
        raise ValidationError("SQS record missing body")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValidationError("SQS body is not valid JSON") from exc
    return JobMessage.from_dict(payload)

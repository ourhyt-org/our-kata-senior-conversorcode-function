import json
import time

import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session

from src.application.dto.conversion_request import ConversionRequest
from src.application.ports.output.mcp_client_port import McpClientPort
from src.domain.entities.mcp_result import McpArtifactFile, McpResult
from src.domain.errors.domain_errors import McpBusinessError, TransientError, ValidationError


class HttpxMcpClient(McpClientPort):
    def __init__(
        self,
        client: httpx.Client | None = None,
        use_aws_iam_auth: bool = False,
        aws_region: str | None = None,
    ):
        timeout = httpx.Timeout(connect=3.0, read=900.0, write=30.0, pool=5.0)
        self._client = client or httpx.Client(timeout=timeout)
        self._use_aws_iam_auth = use_aws_iam_auth
        self._aws_region = aws_region or "us-east-1"

    def convert(self, base_url: str, tool: str | None, request: ConversionRequest, code: str) -> McpResult:
        payload = {
            "languageSelected": request.language_selected,
            "codeToConvert": code,
            "languageTarget": request.language_target,
            "version": request.version,
            "typeArchitected": request.type_architected,
            "options": request.options,
        }

        last_exception: Exception | None = None
        for attempt in range(2):
            try:
                if self._use_aws_iam_auth:
                    body_bytes = json.dumps(payload, ensure_ascii=True).encode("utf-8")
                    headers = self._build_sigv4_headers(base_url=base_url, body_bytes=body_bytes)
                    response = self._client.post(base_url, content=body_bytes, headers=headers)
                else:
                    response = self._client.post(base_url, json=payload)
                if 500 <= response.status_code <= 599:
                    raise TransientError(f"MCP 5xx response: {response.status_code}")
                if response.status_code >= 400:
                    error_body = _extract_error_body(response)
                    raise ValidationError(f"MCP 4xx response: {response.status_code}; body: {error_body}")
                data = response.json()
                normalized = parse_converter_lambda_response(data)
                return parse_mcp_response(normalized)
            except (httpx.TimeoutException, httpx.TransportError, TransientError) as exc:
                last_exception = exc
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                raise TransientError(f"MCP transient failure: {exc}") from exc
            except ValueError as exc:
                raise ValidationError("MCP response is not valid JSON") from exc
        raise TransientError(f"MCP transient failure: {last_exception}")

    def _build_sigv4_headers(self, base_url: str, body_bytes: bytes) -> dict[str, str]:
        session = Session()
        credentials = session.get_credentials()
        if credentials is None:
            raise ValidationError("AWS credentials are not available for MCP_AWS_IAM_AUTH")
        frozen = credentials.get_frozen_credentials()
        aws_request = AWSRequest(
            method="POST",
            url=base_url,
            data=body_bytes,
            headers={"content-type": "application/json"},
        )
        SigV4Auth(frozen, "lambda", self._aws_region).add_auth(aws_request)
        return dict(aws_request.headers.items())


def parse_converter_lambda_response(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValidationError("Invalid MCP response: not an object")

    if "statusCode" in raw and "body" in raw:
        status_code = raw.get("statusCode")
        if not isinstance(status_code, int):
            raise ValidationError("Invalid MCP response: statusCode must be an integer")
        if status_code != 200:
            raise ValidationError(f"MCP converter HTTP error: {status_code}")
        body = raw.get("body")
        if not isinstance(body, str):
            raise ValidationError("Invalid MCP response: body must be a string")
        try:
            parsed_body = json.loads(body)
        except ValueError as exc:
            raise ValidationError("Invalid MCP response: body is not valid JSON") from exc
        if not isinstance(parsed_body, dict):
            raise ValidationError("Invalid MCP response: parsed body must be an object")
        return parsed_body

    return raw


def parse_mcp_response(data: dict) -> McpResult:
    if not isinstance(data, dict):
        raise ValidationError("MCP response must be an object")
    status = str(data.get("status", "")).strip()
    if status not in {"ok", "warning", "error"}:
        raise ValidationError("MCP response has invalid status")

    summary = str(data.get("summary", ""))
    warnings = data.get("warnings") or []
    if not isinstance(warnings, list):
        raise ValidationError("MCP warnings must be a list")
    warnings_list = [_normalize_warning(item) for item in warnings]

    artifacts = data.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        raise ValidationError("MCP artifacts must be an object")
    files_raw = artifacts.get("files") or []
    if not isinstance(files_raw, list):
        raise ValidationError("MCP artifacts.files must be a list")

    files: list[McpArtifactFile] = []
    for item in files_raw:
        if not isinstance(item, dict):
            raise ValidationError("MCP file entry must be an object")
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValidationError("MCP file entry requires path and content strings")
        files.append(McpArtifactFile(path=path, content=content))

    report = artifacts.get("report") or {}
    if not isinstance(report, dict):
        raise ValidationError("MCP artifacts.report must be an object")

    if status in {"ok", "warning"} and len(files) == 0:
        raise ValidationError("MCP success response requires artifacts.files")
    if status == "error":
        raise McpBusinessError(summary or "MCP reported error")

    return McpResult(status=status, summary=summary, warnings=warnings_list, files=files, report=report)


def _normalize_warning(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        code = value.get("code")
        message = value.get("message")
        if isinstance(code, str) and isinstance(message, str):
            return f"{code}: {message}"
        if isinstance(message, str):
            return message
    return str(value)


def _extract_error_body(response: httpx.Response, max_len: int = 2000) -> str:
    try:
        text = response.text
    except Exception:
        return "<unavailable>"
    if not text:
        return "<empty>"
    compact = " ".join(text.split())
    if len(compact) > max_len:
        return compact[:max_len] + "...<truncated>"
    return compact

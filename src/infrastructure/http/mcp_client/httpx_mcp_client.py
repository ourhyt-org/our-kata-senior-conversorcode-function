import time

import httpx

from src.application.dto.conversion_request import ConversionRequest
from src.application.ports.output.mcp_client_port import McpClientPort
from src.domain.entities.mcp_result import McpArtifactFile, McpResult
from src.domain.errors.domain_errors import McpBusinessError, TransientError, ValidationError


class HttpxMcpClient(McpClientPort):
    def __init__(self, client: httpx.Client | None = None):
        timeout = httpx.Timeout(connect=3.0, read=900.0, write=30.0, pool=5.0)
        self._client = client or httpx.Client(timeout=timeout)

    def convert(self, base_url: str, tool: str | None, request: ConversionRequest, code: str) -> McpResult:
        payload = {
            "languageSelected": request.language_selected,
            "codeToConvert": code,
            "languageTarget": request.language_target,
            "version": request.version,
            "typeArchitected": request.type_architected,
        }
        if tool:
            payload["tool"] = tool

        last_exception: Exception | None = None
        for attempt in range(2):
            try:
                response = self._client.post(base_url, json=payload)
                if 500 <= response.status_code <= 599:
                    raise TransientError(f"MCP 5xx response: {response.status_code}")
                if response.status_code >= 400:
                    raise ValidationError(f"MCP 4xx response: {response.status_code}")
                data = response.json()
                return parse_mcp_response(data)
            except (httpx.TimeoutException, httpx.TransportError, TransientError) as exc:
                last_exception = exc
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                raise TransientError(f"MCP transient failure: {exc}") from exc
            except ValueError as exc:
                raise ValidationError("MCP response is not valid JSON") from exc
        raise TransientError(f"MCP transient failure: {last_exception}")


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
    warnings_list = [str(item) for item in warnings]

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

import httpx
import pytest

from src.application.dto.conversion_request import ConversionRequest
from src.domain.errors.domain_errors import McpBusinessError, TransientError, ValidationError
from src.infrastructure.http.mcp_client.httpx_mcp_client import HttpxMcpClient, parse_mcp_response


def test_parse_mcp_error_status_raises_business_error():
    with pytest.raises(McpBusinessError):
        parse_mcp_response(
            {
                "status": "error",
                "summary": "conversion failed",
                "warnings": [],
                "artifacts": {"files": [], "report": {}},
            }
        )


def test_parse_mcp_malformed_files_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_mcp_response(
            {
                "status": "ok",
                "summary": "done",
                "warnings": [],
                "artifacts": {"files": [{"path": "a.py"}], "report": {}},
            }
        )


def test_mcp_client_retries_once_on_5xx_then_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(status_code=503, json={"error": "unavailable"})
        return httpx.Response(
            status_code=200,
            json={
                "status": "ok",
                "summary": "done",
                "warnings": [],
                "artifacts": {
                    "files": [{"path": "main.py", "content": "print('ok')"}],
                    "report": {"score": 1},
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=httpx.Timeout(3.0, read=10.0))
    mcp = HttpxMcpClient(client=client)

    result = mcp.convert(
        base_url="https://mcp.test/convert",
        tool="convert_code",
        request=ConversionRequest(
            language_selected="cobol",
            language_target="python",
            version="1",
            type_architected="clean",
            options={},
        ),
        code="IDENTIFICATION DIVISION.",
    )

    assert calls["count"] == 2
    assert result.status == "ok"


def test_mcp_client_raises_transient_after_retry_exhausted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=503, json={"error": "unavailable"})

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=httpx.Timeout(3.0, read=10.0))
    mcp = HttpxMcpClient(client=client)

    with pytest.raises(TransientError):
        mcp.convert(
            base_url="https://mcp.test/convert",
            tool=None,
            request=ConversionRequest(
                language_selected="cobol",
                language_target="python",
                version="1",
                type_architected="clean",
                options={},
            ),
            code="IDENTIFICATION DIVISION.",
        )

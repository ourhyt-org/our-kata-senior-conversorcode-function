import pytest

from src.application.dto.conversion_request import ConversionRequest
from src.domain.errors.domain_errors import McpBusinessError
from src.infrastructure.http.mcp_client.mock_mcp_client import MockMcpClient


def _request() -> ConversionRequest:
    return ConversionRequest(
        language_selected="cobol",
        language_target="python",
        version="1",
        type_architected="clean",
        options={},
    )


def test_mock_mcp_ok_mode_returns_artifact():
    client = MockMcpClient(mode="ok")
    result = client.convert("mock://mcp", "convert_code", _request(), "IDENTIFICATION DIVISION.")

    assert result.status == "ok"
    assert len(result.files) == 1
    assert result.files[0].path.endswith(".py")


def test_mock_mcp_warning_mode_returns_warning_status():
    client = MockMcpClient(mode="warning")
    result = client.convert("mock://mcp", "convert_code", _request(), "IDENTIFICATION DIVISION.")

    assert result.status == "warning"
    assert len(result.warnings) == 1


def test_mock_mcp_error_mode_raises_business_error():
    client = MockMcpClient(mode="error")
    with pytest.raises(McpBusinessError):
        client.convert("mock://mcp", "convert_code", _request(), "IDENTIFICATION DIVISION.")

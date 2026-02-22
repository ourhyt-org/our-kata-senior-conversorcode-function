import pytest

from src.domain.entities.mcp_result import McpArtifactFile
from src.domain.errors.domain_errors import LimitsExceededError, PathTraversalError
from src.infrastructure.packaging.zip_packager import build_outputs, sanitize_zip_path


def test_sanitize_valid_path():
    assert sanitize_zip_path("src/main.py") == "src/main.py"


def test_sanitize_rejects_traversal():
    with pytest.raises(PathTraversalError):
        sanitize_zip_path("../evil.py")


def test_sanitize_rejects_absolute():
    with pytest.raises(PathTraversalError):
        sanitize_zip_path("/etc/passwd")


def test_sanitize_rejects_windows_drive():
    with pytest.raises(PathTraversalError):
        sanitize_zip_path("C:\\temp\\file.txt")


def test_build_outputs_enforces_limits():
    files = [McpArtifactFile(path=f"f{i}.txt", content="x") for i in range(3)]
    with pytest.raises(LimitsExceededError):
        build_outputs(
            files=files,
            status="ok",
            summary="done",
            warnings=[],
            report={},
            max_files=2,
            max_zip_mb=1,
        )

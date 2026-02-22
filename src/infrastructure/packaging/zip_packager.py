import io
import json
import ntpath
import posixpath
import re
import zipfile

from src.domain.entities.mcp_result import McpArtifactFile
from src.domain.errors.domain_errors import LimitsExceededError, PathTraversalError, ValidationError


def sanitize_zip_path(path: str) -> str:
    if not path or not path.strip():
        raise PathTraversalError("Empty path is not allowed")
    if ntpath.splitdrive(path)[0]:
        raise PathTraversalError("Drive letter paths are not allowed")
    normalized = path.replace("\\", "/")
    normalized = posixpath.normpath(normalized)
    if normalized in {".", ""}:
        raise PathTraversalError("Invalid path")
    if normalized.startswith("/"):
        raise PathTraversalError("Absolute paths are not allowed")
    if normalized.startswith("../") or normalized == "..":
        raise PathTraversalError("Path traversal is not allowed")
    segments = normalized.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise PathTraversalError("Invalid path segments")
    if re.match(r"^[A-Za-z]:", normalized):
        raise PathTraversalError("Windows absolute paths are not allowed")
    return normalized


def build_outputs(
    files: list[McpArtifactFile],
    status: str,
    summary: str,
    warnings: list[str],
    report: dict,
    max_files: int,
    max_zip_mb: int,
) -> tuple[bytes, dict]:
    if len(files) > max_files:
        raise LimitsExceededError(f"Too many files: {len(files)} > {max_files}")

    max_zip_bytes = max_zip_mb * 1024 * 1024
    total_uncompressed = 0

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            safe_path = sanitize_zip_path(file.path)
            encoded = file.content.encode("utf-8")
            total_uncompressed += len(encoded)
            if total_uncompressed > max_zip_bytes:
                raise LimitsExceededError("Total uncompressed artifact size exceeded")
            zf.writestr(safe_path, encoded)

    zip_bytes = buffer.getvalue()
    if len(zip_bytes) > max_zip_bytes:
        raise LimitsExceededError("Final zip size exceeded")

    report_json = {
        "status": status,
        "summary": summary,
        "warnings": warnings,
        "report": report,
        "fileCount": len(files),
        "zipSizeBytes": len(zip_bytes),
    }
    try:
        json.dumps(report_json)
    except TypeError as exc:
        raise ValidationError("report payload is not JSON serializable") from exc

    return zip_bytes, report_json

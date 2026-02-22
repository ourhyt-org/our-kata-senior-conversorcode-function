import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ddb_table: str
    output_bucket: str
    mcp_base_url: str | None
    mcp_use_mock: bool
    mcp_mock_mode: str
    max_files: int
    max_zip_mb: int
    log_level: str
    stale_running_minutes: int = 20


class SettingsError(Exception):
    pass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SettingsError(f"Missing required environment variable: {name}")
    return value


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SettingsError(f"Invalid boolean value: {value}")


def load_settings() -> Settings:
    mcp_mock_mode = os.getenv("MCP_MOCK_MODE", "ok").strip().lower()
    if mcp_mock_mode not in {"ok", "warning", "error"}:
        raise SettingsError("MCP_MOCK_MODE must be one of: ok, warning, error")
    return Settings(
        ddb_table=_require_env("DDB_TABLE"),
        output_bucket=_require_env("OUTPUT_BUCKET"),
        mcp_base_url=os.getenv("MCP_BASE_URL"),
        mcp_use_mock=_parse_bool(os.getenv("MCP_USE_MOCK"), False),
        mcp_mock_mode=mcp_mock_mode,
        max_files=int(os.getenv("MAX_FILES", "200")),
        max_zip_mb=int(os.getenv("MAX_ZIP_MB", "50")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ddb_table: str
    output_bucket: str
    mcp_base_url: str | None
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


def load_settings() -> Settings:
    return Settings(
        ddb_table=_require_env("DDB_TABLE"),
        output_bucket=_require_env("OUTPUT_BUCKET"),
        mcp_base_url=os.getenv("MCP_BASE_URL"),
        max_files=int(os.getenv("MAX_FILES", "200")),
        max_zip_mb=int(os.getenv("MAX_ZIP_MB", "50")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

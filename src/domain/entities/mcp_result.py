from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class McpArtifactFile:
    path: str
    content: str


@dataclass(frozen=True)
class McpResult:
    status: str
    summary: str
    warnings: list[str]
    files: list[McpArtifactFile]
    report: dict[str, Any]

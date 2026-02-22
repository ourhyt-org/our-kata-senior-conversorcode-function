from abc import ABC, abstractmethod

from src.application.dto.conversion_request import ConversionRequest
from src.domain.entities.mcp_result import McpResult


class McpClientPort(ABC):
    @abstractmethod
    def convert(self, base_url: str, tool: str | None, request: ConversionRequest, code: str) -> McpResult:
        raise NotImplementedError

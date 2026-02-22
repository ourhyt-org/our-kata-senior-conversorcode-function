from src.application.dto.conversion_request import ConversionRequest
from src.application.ports.output.mcp_client_port import McpClientPort
from src.domain.entities.mcp_result import McpArtifactFile, McpResult
from src.domain.errors.domain_errors import McpBusinessError


class MockMcpClient(McpClientPort):
    def __init__(self, mode: str = "ok"):
        self._mode = mode

    def convert(self, base_url: str, tool: str | None, request: ConversionRequest, code: str) -> McpResult:
        if self._mode == "error":
            raise McpBusinessError("Mock MCP forced error mode")

        extension = _target_extension(request.language_target)
        file_path = f"src/generated/main.{extension}"
        content = _mock_content(request.language_target, request.type_architected)
        warnings = ["mock-warning: simulated conversion warning"] if self._mode == "warning" else []
        status = "warning" if self._mode == "warning" else "ok"

        return McpResult(
            status=status,
            summary="Mock MCP conversion completed",
            warnings=warnings,
            files=[McpArtifactFile(path=file_path, content=content)],
            report={
                "provider": "mock-mcp",
                "languageSelected": request.language_selected,
                "languageTarget": request.language_target,
                "typeArchitected": request.type_architected,
                "codeSizeBytes": len(code.encode("utf-8")),
                "mode": self._mode,
            },
        )


def _target_extension(language_target: str) -> str:
    mapping = {
        "python": "py",
        "java": "java",
        "go": "go",
        "node": "js",
    }
    return mapping.get(language_target.lower(), "txt")


def _mock_content(language_target: str, type_architected: str) -> str:
    target = language_target.lower()
    if target == "python":
        return f"def main():\n    return 'mock-{type_architected}'\n"
    if target == "java":
        return "public class Main { public static void main(String[] args) { System.out.println(\"mock\"); } }\n"
    if target == "go":
        return "package main\n\nfunc main() {}\n"
    if target == "node":
        return "function main() { return 'mock'; }\nmodule.exports = { main };\n"
    return "mock output\n"

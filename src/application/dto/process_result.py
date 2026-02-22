from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessResult:
    success: bool
    retriable: bool
    no_op: bool = False
    message: str | None = None

import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.application.ports.output.logger_port import LoggerPort


class JsonLogger(LoggerPort):
    def __init__(self, logger: logging.Logger, context: dict[str, Any] | None = None):
        self._logger = logger
        self._context = context or {}

    def with_context(self, **kwargs: Any) -> LoggerPort:
        new_context = dict(self._context)
        new_context.update(kwargs)
        return JsonLogger(self._logger, new_context)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log("ERROR", message, **kwargs)

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        payload.update(self._context)
        payload.update(kwargs)
        self._logger.log(_to_logging_level(level), json.dumps(payload, ensure_ascii=True))


def _to_logging_level(level: str) -> int:
    if level == "ERROR":
        return logging.ERROR
    if level == "WARNING":
        return logging.WARNING
    return logging.INFO


def build_logger(name: str, level: str) -> JsonLogger:
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level.upper())
        logger.addHandler(handler)
    return JsonLogger(logger)

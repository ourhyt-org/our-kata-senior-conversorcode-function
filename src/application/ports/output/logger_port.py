from abc import ABC, abstractmethod
from typing import Any


class LoggerPort(ABC):
    @abstractmethod
    def with_context(self, **kwargs: Any) -> "LoggerPort":
        raise NotImplementedError

    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        raise NotImplementedError

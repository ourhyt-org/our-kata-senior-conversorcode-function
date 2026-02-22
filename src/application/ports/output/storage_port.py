from abc import ABC, abstractmethod
from typing import Any


class StoragePort(ABC):
    @abstractmethod
    def get_json(self, bucket: str, key: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_text(self, bucket: str, key: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def put_bytes(self, bucket: str, key: str, content: bytes, content_type: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def put_json(self, bucket: str, key: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, bucket: str, key: str) -> bool:
        raise NotImplementedError

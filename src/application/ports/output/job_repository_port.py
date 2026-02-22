from abc import ABC, abstractmethod

from src.domain.entities.job import JobRecord


class JobRepositoryPort(ABC):
    @abstractmethod
    def get_job(self, job_id: str) -> JobRecord | None:
        raise NotImplementedError

    @abstractmethod
    def mark_running(self, job_id: str, started_at_iso: str, stale_before_iso: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def mark_finished(self, job_id: str, finished_at_iso: str, output_s3_key: str, report_s3_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def mark_failed(self, job_id: str, finished_at_iso: str, error_message: str) -> None:
        raise NotImplementedError

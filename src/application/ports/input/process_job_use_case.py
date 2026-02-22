from abc import ABC, abstractmethod

from src.application.dto.job_message import JobMessage
from src.application.dto.process_result import ProcessResult


class ProcessJobUseCase(ABC):
    @abstractmethod
    def execute(self, message: JobMessage) -> ProcessResult:
        raise NotImplementedError

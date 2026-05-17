from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    success: bool
    output_path: str = ''
    drive_url: str = ''
    rows_affected: int = 0
    logs: str = ''
    error: str = ''
    extra: dict[str, Any] = field(default_factory=dict)


class BaseStep(ABC):
    on_error: str = 'stop'  # 'stop' | 'continue'

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self.on_error = config.get('on_error', 'stop')

    @abstractmethod
    def run(self, context: dict[str, Any]) -> StepResult: ...

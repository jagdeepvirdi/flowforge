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
    output_variables: dict[str, Any] = field(default_factory=dict)
    # bulk_load output fields
    files_found: int = 0
    files_loaded: int = 0
    files_failed: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    duration_sec: float = 0.0


class BaseStep(ABC):
    on_error: str = 'stop'  # 'stop' | 'continue'
    step_type: str = ''     # overridden by each concrete step class

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self.on_error = config.get('on_error', 'stop')

    @abstractmethod
    def run(self, context: dict[str, Any]) -> StepResult: ...

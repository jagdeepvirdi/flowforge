import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*$')


def validate_identifier(name: str, field_name: str = 'table name') -> None:
    """Raise ValueError if name is unsafe for SQL identifier interpolation."""
    if not _IDENT_RE.match(name):
        raise ValueError(
            f"Invalid {field_name} '{name}': only letters, digits, underscores, and dots allowed"
        )


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
    # db_query capture_rows output fields
    rows: list[dict] = field(default_factory=list)
    table_html: str = ''
    kv_html: str = ''
    # ai_analyze output field — also injected into top-level context via output_variables
    ai_summary: str = ''


class BaseStep(ABC):
    on_error: str = 'stop'  # 'stop' | 'continue'
    step_type: str = ''     # overridden by each concrete step class

    def __init__(self, name: str, config: dict[str, Any]):
        self.name           = name
        self.config         = config
        self.on_error       = config.get('on_error', 'stop')
        self.parallel_group = config.get('parallel_group') or None
        self.db_step_order  = int(config.get('_db_step_order', 0))

    @abstractmethod
    def run(self, context: dict[str, Any]) -> StepResult: ...

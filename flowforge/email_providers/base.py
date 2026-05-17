from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EmailResult:
    success: bool
    error: str = ''
    recipients: list[str] = field(default_factory=list)


class EmailProvider(ABC):
    @abstractmethod
    def send(
        self,
        to: list[str],
        cc: list[str],
        bcc: list[str],
        subject: str,
        html_body: str,
        attachments: list[Path],
    ) -> EmailResult: ...

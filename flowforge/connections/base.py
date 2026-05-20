from abc import ABC, abstractmethod
from typing import Any


class BaseConnection(ABC):
    @abstractmethod
    def execute_procedure(self, name: str, params: dict[str, Any]) -> None: ...

    @abstractmethod
    def execute_query(self, sql: str, params: tuple = ()) -> list[tuple]: ...

    @abstractmethod
    def execute_query_with_columns(self, sql: str, params: tuple = ()) -> tuple[list[tuple], list[str]]: ...

    @abstractmethod
    def execute_write(self, sql: str, params: tuple = ()) -> int: ...

    @abstractmethod
    def test(self) -> tuple[bool, int]: ...

    @abstractmethod
    def close(self) -> None: ...

    def __enter__(self) -> 'BaseConnection':
        return self

    def __exit__(self, *_) -> None:
        self.close()

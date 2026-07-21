"""Generic registration primitive for FlowForge's pluggable categories.

One `Registry` instance per category (steps, connections, email_providers, ...)
replaces that category's hardcoded if/elif dispatch with `.register()` /
`.get()` / `.list()` / `.metadata()`. This module only provides the primitive
itself — wiring individual categories through it is tracked separately
(see docs/TASKS.md, Phase 13.2/13.3).
"""
from dataclasses import asdict, dataclass
from typing import Any, TypeVar

T = TypeVar('T')


@dataclass(frozen=True)
class IntegrationSpec:
    """Structured metadata describing one registered class.

    A category migrating onto `Registry` (Phase 13.2/13.3) passes one of these
    via `Registry.register_spec()` instead of loose `**metadata` kwargs, so
    every registered entry carries the same shape.
    """
    key: str
    display_name: str
    description: str = ''
    requires: str | None = None       # pip extra name, e.g. "oracle" -> `pip install flowforge[oracle]`
    config_schema: dict[str, Any] | None = None  # optional, for future generic frontend forms
    tier: str | None = None           # unenforced — no entitlement system reads this yet (see ARCH-11)


class Registry:
    """Maps string keys (e.g. a `db_type` or `provider_type`) to a registered value plus metadata.

    The registered value is usually a class, but doesn't have to be — a category
    can register anything (e.g. connections/factory.py registers a
    `(dotted_class_path, kwargs_builder)` tuple instead of an imported class, to
    keep optional driver imports lazy). `Registry` itself doesn't care.
    """

    def __init__(self, category: str):
        self.category = category
        self._classes: dict[str, Any] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(self, key: str, cls: T | None = None, **metadata: Any):
        """Register `cls` under `key` with optional metadata.

        Usable directly:
            registry.register('postgresql', PostgreSQLConnection, display_name='PostgreSQL')

        Or as a decorator:
            @registry.register('postgresql', display_name='PostgreSQL')
            class PostgreSQLConnection(BaseConnection): ...
        """
        if cls is not None:
            self._do_register(key, cls, metadata)
            return cls

        def decorator(cls_: T) -> T:
            self._do_register(key, cls_, metadata)
            return cls_
        return decorator

    def register_spec(self, spec: IntegrationSpec, cls: T | None = None):
        """Register `cls` under `spec.key` using an `IntegrationSpec` instead of loose kwargs.

        Usable directly or as a decorator, same as `.register()`.
        """
        if cls is not None:
            self._do_register(spec.key, cls, asdict(spec))
            return cls

        def decorator(cls_: T) -> T:
            self._do_register(spec.key, cls_, asdict(spec))
            return cls_
        return decorator

    def _do_register(self, key: str, cls: Any, metadata: dict[str, Any]) -> None:
        if key in self._classes:
            raise ValueError(
                f"{self.category}: '{key}' is already registered to {self._classes[key]!r}"
            )
        self._classes[key] = cls
        self._metadata[key] = metadata

    def get(self, key: str) -> Any:
        try:
            return self._classes[key]
        except KeyError:
            raise KeyError(f"{self.category}: unknown key '{key}'") from None

    def list(self) -> list[str]:
        return sorted(self._classes)

    def metadata(self, key: str) -> dict[str, Any]:
        if key not in self._metadata:
            raise KeyError(f"{self.category}: unknown key '{key}'")
        return self._metadata[key]

    def spec(self, key: str) -> IntegrationSpec:
        """Return the `IntegrationSpec` for `key` (only valid if registered via `register_spec()`)."""
        return IntegrationSpec(**self.metadata(key))

    def unregister(self, key: str) -> None:
        """Remove a registration (e.g. a plugin registered class being reset between test runs)."""
        if key not in self._classes:
            raise KeyError(f"{self.category}: unknown key '{key}'")
        del self._classes[key]
        del self._metadata[key]

    def __contains__(self, key: str) -> bool:
        return key in self._classes

    def __len__(self) -> int:
        return len(self._classes)

    def _reset_for_tests(self) -> None:
        """Test-only: drop all registrations so a test module can start clean."""
        self._classes.clear()
        self._metadata.clear()

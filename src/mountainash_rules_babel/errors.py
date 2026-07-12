from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from mountainash_rules_babel.validators.base import ValidationReport


class BabelError(Exception):
    pass


class FormatNotFoundError(BabelError):
    def __init__(self, format_name: str, available: list[str] | None = None) -> None:
        self.format_name = format_name
        self.available = available or []
        available_str = ", ".join(self.available) if self.available else "none"
        super().__init__(
            f"Format '{format_name}' not found. Available formats: {available_str}"
        )


class ImportError_(BabelError):
    pass


class ExportError(BabelError):
    pass


class DecompositionError(BabelError):
    pass


class ValidationError(BabelError):
    def __init__(self, message: str, report: ValidationReport | None = None) -> None:
        self.report = report
        super().__init__(message)


class DependencyMissingError(BabelError, ImportError):
    pass


class SchemaContractError(BabelError):
    """A lattice frame violates the flat/composed schema contract."""

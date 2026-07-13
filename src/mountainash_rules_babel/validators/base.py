from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from mountainash_rules import Lattice


@dataclass
class ValidationIssue:
    severity: Literal["error", "warning", "info"]
    category: str
    message: str
    details: dict | None = None


@dataclass
class ValidationReport:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    input_row_count: int | None = None
    output_row_count: int | None = None
    exact_match: bool | None = None
    fragment_count: int | None = None
    combination_count: int | None = None
    conflict_count: int = 0
    coverage_gap_count: int = 0
    orphan_count: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


@runtime_checkable
class Validator(Protocol):
    name: str

    def validate(self, lattice: Lattice, **options) -> ValidationReport: ...

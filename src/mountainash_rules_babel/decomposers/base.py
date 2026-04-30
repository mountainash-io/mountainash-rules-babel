from __future__ import annotations

import typing as t
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from mountainash_utils_rules.aggregate import Aggregate
from mountainash_utils_rules.dimension import DimensionsMetadata
from mountainash_utils_rules.lattice import Lattice

from mountainash_rules_babel.validators.base import ValidationReport


@dataclass
class Fragment:
    name: str
    dataframe: t.Any
    dimensions: list[str]
    metadata: DimensionsMetadata
    aggregates: list[Aggregate]
    source_rows: list[int] | None = None


@dataclass
class DecompositionResult:
    fragments: list[Fragment]
    metadata: DimensionsMetadata
    aggregates: list[Aggregate]
    original_row_count: int
    fragment_count: int
    dimension_groups: list[list[str]]
    validation: ValidationReport | None = None


@runtime_checkable
class Decomposer(Protocol):
    name: str

    def decompose(self, lattice: Lattice, **options) -> DecompositionResult: ...

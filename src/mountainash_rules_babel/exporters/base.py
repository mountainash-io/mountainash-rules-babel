from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import polars as pl
from mountainash_rules import DimensionsMetadata, Lattice, MatchStrategy

from mountainash_rules_babel.errors import SchemaContractError


@runtime_checkable
class Exporter(Protocol):
    name: str
    file_extension: str

    def export(self, lattice: Lattice, path: Path, **options) -> Path: ...

    def export_bytes(self, lattice: Lattice, **options) -> bytes: ...


def lattice_to_polars(lattice: Lattice) -> pl.DataFrame:
    """Materialise a Lattice's combinations as a polars DataFrame, whatever the backend."""
    combos = lattice.combinations
    if isinstance(combos, pl.DataFrame):
        return combos
    from mountainash.relations import relation

    return relation(combos).to_polars()


@dataclass
class LatticeView:
    df: pl.DataFrame
    metadata: DimensionsMetadata
    output_columns: list[str]


def _dimension_value_columns(metadata: DimensionsMetadata) -> list[str]:
    cols: list[str] = []
    for dimension in metadata.dimensions:
        if dimension.match_strategy == MatchStrategy.RANGE:
            cols.extend([dimension.range_min_field, dimension.range_max_field])
        else:
            cols.append(dimension.resolved_rule_field)
    return cols


def resolve_lattice(lattice) -> LatticeView:
    """Return inspection-only flat values for CSV and DMN adapters."""
    if lattice.artifact_kind == "exact_cells":
        raise SchemaContractError(
            "Exact-native lattices cannot be exported as flat values; "
            "use format='native'"
        )
    if lattice.artifact_kind is not None:
        raise SchemaContractError(
            f"Unsupported lattice artifact kind {lattice.artifact_kind!r}"
        )

    df = lattice_to_polars(lattice)
    dimension_columns = _dimension_value_columns(lattice.metadata)
    output_columns = [
        column
        for column in df.columns
        if column not in dimension_columns and column != "rule_name"
    ]
    return LatticeView(
        df=df,
        metadata=lattice.metadata,
        output_columns=output_columns,
    )

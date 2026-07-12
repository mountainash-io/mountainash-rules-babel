from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import polars as pl

from mountainash_rules.lattice import Lattice


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


from dataclasses import dataclass, field

from mountainash_rules.constants import MatchStrategy
from mountainash_rules.dimension import DimensionsMetadata

from mountainash_rules_babel.errors import SchemaContractError

TRACKING_COLUMNS = ("__prime", "__prime_product", "__level")


@dataclass
class LatticeView:
    df: pl.DataFrame
    metadata: DimensionsMetadata
    is_composed: bool
    output_columns: list[str]
    dropped_stale: list[str] = field(default_factory=list)
    tracking: "pl.DataFrame | None" = None


def _dimension_value_columns(metadata: DimensionsMetadata) -> list[str]:
    cols: list[str] = []
    for d in metadata.dimensions:
        if d.match_strategy == MatchStrategy.RANGE:
            cols.extend([d.range_min_field, d.range_max_field])
        else:
            cols.append(d.resolved_rule_field)
    return cols


def resolve_lattice(lattice, *, include_tracking: bool = False) -> LatticeView:
    """Normalise a lattice to authoritative values under flat column names."""
    df = lattice_to_polars(lattice)
    dim_cols = _dimension_value_columns(lattice.metadata)

    if not lattice.is_composed:
        tracked = [
            c for c in df.columns
            if c in TRACKING_COLUMNS or c.startswith("__agg_")
        ]
        if tracked:
            raise SchemaContractError(
                f"Flat lattice contains tracking columns {tracked}; "
                f"mixed shapes are not exportable"
            )
        output_columns = [
            c for c in df.columns if c not in dim_cols and c != "rule_name"
        ]
        return LatticeView(
            df=df, metadata=lattice.metadata, is_composed=False,
            output_columns=output_columns,
        )

    # Composed: co_ columns are authoritative; anchor copies are stale.
    co_renames = {f"co_{c}": c for c in dim_cols}
    na_cols = [c for c in df.columns if c.startswith("co_") and c.endswith("_na")]
    agg_renames = {
        c: c.removeprefix("__agg_")
        for c in df.columns if c.startswith("__agg_")
    }
    tracking_cols = [c for c in df.columns if c in TRACKING_COLUMNS]

    keep = list(co_renames) + list(agg_renames)
    stale = [
        c for c in df.columns
        if c not in keep and c not in na_cols and c not in tracking_cols
    ]
    for src, dst in agg_renames.items():
        if dst in co_renames.values():
            raise SchemaContractError(
                f"Aggregate column {src} would rename onto dimension "
                f"column {dst}"
            )

    tracking = df.select(tracking_cols) if include_tracking else None
    out = df.select(keep).rename({**co_renames, **agg_renames})
    return LatticeView(
        df=out,
        metadata=lattice.metadata,
        is_composed=True,
        output_columns=sorted(agg_renames.values()),
        dropped_stale=sorted(stale),
        tracking=tracking,
    )

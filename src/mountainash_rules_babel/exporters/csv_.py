from __future__ import annotations

from pathlib import Path

import polars as pl

from mountainash_rules import DataType, Lattice, MatchStrategy, sentinels_for

from mountainash_rules_babel.exporters.base import resolve_lattice
from mountainash_rules_babel.manifest import LatticeManifest


def _sentinels_to_null(df: pl.DataFrame, lattice: Lattice) -> pl.DataFrame:
    """Blank only declared dimension sentinels at the CSV boundary."""
    exprs = []
    for dimension in lattice.metadata.dimensions:
        if dimension.data_type is DataType.BOOL or dimension.match_strategy in {
            MatchStrategy.SET_MEMBERSHIP,
            MatchStrategy.SET_EXCLUSION,
        }:
            continue
        columns = (
            [dimension.range_min_field, dimension.range_max_field]
            if dimension.match_strategy == MatchStrategy.RANGE
            else [dimension.resolved_rule_field]
        )
        for column in columns:
            if column in df.columns:
                exprs.append(
                    pl.when(pl.col(column).is_in(sentinels_for(dimension.data_type)))
                    .then(None)
                    .otherwise(pl.col(column))
                    .alias(column)
                )
    return df.with_columns(exprs) if exprs else df


class CsvExporter:
    name: str = "csv"
    file_extension: str = ".csv"

    def _frame(self, lattice: Lattice) -> pl.DataFrame:
        view = resolve_lattice(lattice)
        return _sentinels_to_null(view.df, lattice)

    def export(
        self,
        lattice: Lattice,
        path: Path,
        *,
        manifest_sidecar: bool = True,
        **options,
    ) -> Path:
        path = Path(path)
        self._frame(lattice).write_csv(path)
        if manifest_sidecar:
            LatticeManifest.for_lattice(lattice).to_yaml_file(
                path.with_suffix(".manifest.yaml")
            )
        return path

    def export_bytes(self, lattice: Lattice, **options) -> bytes:
        csv_str = self._frame(lattice).write_csv()
        return csv_str.encode("utf-8") if isinstance(csv_str, str) else csv_str

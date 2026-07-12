from __future__ import annotations

from pathlib import Path

import polars as pl

from mountainash_rules.constants import (
    NOT_SET,
    NOT_SET_DATE,
    NOT_SET_DATETIME,
    NOT_SET_NUMERIC,
    UNKNOWN,
    UNKNOWN_DATE,
    UNKNOWN_DATETIME,
    UNKNOWN_NUMERIC,
)
from mountainash_rules.lattice import Lattice

from mountainash_rules_babel.exporters.base import resolve_lattice
from mountainash_rules_babel.manifest import LatticeManifest

_STRING_SENTINELS = [UNKNOWN, NOT_SET]
_NUMERIC_SENTINELS = [UNKNOWN_NUMERIC, NOT_SET_NUMERIC]
_DATE_SENTINELS = [UNKNOWN_DATE, NOT_SET_DATE]
_DATETIME_SENTINELS = [UNKNOWN_DATETIME, NOT_SET_DATETIME]


def _sentinels_to_null(df: pl.DataFrame) -> pl.DataFrame:
    """Blank out typed sentinel values so they export as empty cells."""
    exprs = []
    for name, dtype in df.schema.items():
        if dtype == pl.Utf8:
            sentinels: list = _STRING_SENTINELS
        elif dtype == pl.Date:
            sentinels = _DATE_SENTINELS
        elif dtype == pl.Datetime or isinstance(dtype, pl.Datetime):
            sentinels = _DATETIME_SENTINELS
        elif dtype.is_numeric():
            sentinels = _NUMERIC_SENTINELS
        else:
            continue
        exprs.append(
            pl.when(pl.col(name).is_in(sentinels))
            .then(None).otherwise(pl.col(name)).alias(name)
        )
    return df.with_columns(exprs) if exprs else df


class CsvExporter:
    name: str = "csv"
    file_extension: str = ".csv"

    def _frame(self, lattice: Lattice, include_tracking: bool) -> pl.DataFrame:
        view = resolve_lattice(lattice, include_tracking=include_tracking)
        df = _sentinels_to_null(view.df)
        if include_tracking and view.tracking is not None:
            df = pl.concat([df, view.tracking], how="horizontal")
        return df

    def export(
        self,
        lattice: Lattice,
        path: Path,
        *,
        include_tracking: bool = False,
        manifest_sidecar: bool = True,
        **options,
    ) -> Path:
        path = Path(path)
        self._frame(lattice, include_tracking).write_csv(path)
        if manifest_sidecar:
            LatticeManifest.for_lattice(lattice).to_yaml_file(
                path.with_suffix(".manifest.yaml")
            )
        return path

    def export_bytes(
        self, lattice: Lattice, *, include_tracking: bool = False, **options
    ) -> bytes:
        csv_str = self._frame(lattice, include_tracking).write_csv()
        return csv_str.encode("utf-8") if isinstance(csv_str, str) else csv_str

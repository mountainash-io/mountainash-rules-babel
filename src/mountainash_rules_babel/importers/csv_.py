from __future__ import annotations

import pathlib
import warnings
from pathlib import Path

import polars as pl
import yaml

from mountainash_rules.aggregate import Aggregate
from mountainash_rules.constants import MatchStrategy, unknown_sentinel_for
from mountainash_rules.dimension import Dimension, DimensionsMetadata
from mountainash_rules.lattice import Lattice

from mountainash_rules_babel.exporters.base import TRACKING_COLUMNS
from mountainash_rules_babel.manifest import LatticeManifest


class CsvImporter:
    name: str = "csv"
    file_extensions: list[str] = [".csv"]

    def import_lattice(
        self,
        path: Path,
        *,
        metadata: DimensionsMetadata | str | Path | None = None,
        dimension_columns: list[str] | None = None,
        aggregate_columns: dict[str, str] | None = None,
        **options,
    ) -> Lattice:
        path = Path(path)
        df = pl.read_csv(path)

        # Strip tracking columns: imports never carry composed state.
        tracked = [
            c for c in df.columns
            if c in TRACKING_COLUMNS or c.startswith("__agg_")
        ]
        if tracked:
            warnings.warn(
                f"Stripping tracking columns on import: {tracked} "
                f"(diagnostic output only; recombination is "
                f"AccumulatorEngine.build()'s job)",
                UserWarning,
            )
            df = df.drop(tracked)

        manifest: LatticeManifest | None = None
        sidecar = path.with_suffix(".manifest.yaml")
        if metadata is None and sidecar.exists():
            manifest = LatticeManifest.from_yaml_file(sidecar)
            metadata = manifest.dimensions

        if metadata is not None:
            if isinstance(metadata, (str, pathlib.Path)):
                loaded = yaml.safe_load(Path(metadata).read_text())
                # A manifest's `dimensions` key holds the DimensionsMetadata
                # mapping; bare metadata YAML holds a list of dimensions.
                if isinstance(loaded.get("dimensions"), dict):
                    manifest = LatticeManifest.from_yaml_file(metadata)
                    metadata = manifest.dimensions
                else:
                    metadata = DimensionsMetadata.from_yaml_file(metadata)
            df = self._fill_sentinels(df, metadata)
            self._validate_columns(df, metadata)
            aggregates = (
                [Aggregate(column_name=a.column_name, operation=a.operation)
                 for a in manifest.aggregates]
                if manifest is not None
                else [Aggregate(column_name=c, operation=op)
                      for c, op in (aggregate_columns or {}).items()]
            )
            return Lattice(
                dataframe=df,
                metadata=metadata,
                aggregates=aggregates,
                partition_key=None,
            )

        if dimension_columns is None:
            non_agg = set((aggregate_columns or {}).keys())
            dimension_columns = [c for c in df.columns if c not in non_agg and c != "rule_name"]

        dimensions = []
        for col_name in dimension_columns:
            dtype = df.schema[col_name]
            py_type: type = str
            if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
                py_type = int
            elif dtype in (pl.Float32, pl.Float64):
                py_type = float

            dimensions.append(
                Dimension(
                    dimension_name=col_name,
                    match_strategy=MatchStrategy.EXACT,
                    data_type=py_type,
                )
            )

        metadata = DimensionsMetadata(dimensions=dimensions)

        aggregates = []
        if aggregate_columns:
            for col_name, operation in aggregate_columns.items():
                aggregates.append(Aggregate(column_name=col_name, operation=operation))

        return Lattice(
            dataframe=df,
            metadata=metadata,
            aggregates=aggregates,
            partition_key=None,
        )

    @staticmethod
    def _fill_sentinels(
        df: pl.DataFrame, metadata: DimensionsMetadata
    ) -> pl.DataFrame:
        """Fill empty cells in dimension columns with typed UNKNOWN sentinels."""
        exprs = []
        for dim in metadata.dimensions:
            sentinel = unknown_sentinel_for(dim.data_type)
            if dim.match_strategy == MatchStrategy.RANGE:
                cols = [dim.range_min_field, dim.range_max_field]
            else:
                cols = [dim.resolved_rule_field]
            for c in cols:
                if c in df.columns:
                    exprs.append(pl.col(c).fill_null(sentinel))
        return df.with_columns(exprs) if exprs else df

    @staticmethod
    def _validate_columns(df: pl.DataFrame, metadata: DimensionsMetadata) -> None:
        missing: list[str] = []
        for dim in metadata.dimensions:
            if dim.match_strategy == MatchStrategy.RANGE:
                needed = [dim.range_min_field, dim.range_max_field]
            else:
                needed = [dim.resolved_rule_field]
            missing.extend(c for c in needed if c not in df.columns)
        if missing:
            raise ValueError(
                f"Metadata references columns missing from CSV: {missing}"
            )

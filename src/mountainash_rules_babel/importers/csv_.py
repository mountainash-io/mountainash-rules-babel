from __future__ import annotations

import pathlib
from pathlib import Path

import polars as pl
import yaml

from mountainash_rules import (
    Aggregate,
    DataType,
    Dimension,
    DimensionsMetadata,
    Lattice,
    MatchStrategy,
    unknown_sentinel_for,
)

from mountainash_rules_babel.manifest import LatticeManifest


_POLARS_TYPES = {
    DataType.STR: pl.String,
    DataType.INT: pl.Int64,
    DataType.FLOAT: pl.Float64,
    DataType.BOOL: pl.Boolean,
    DataType.DATE: pl.Date,
    DataType.DATETIME: pl.Datetime,
}


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

        sidecar = path.with_suffix(".manifest.yaml")
        manifest = LatticeManifest.from_yaml_file(sidecar) if sidecar.exists() else None
        if metadata is None and manifest is not None:
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
                [
                    Aggregate(column_name=a.column_name, operation=a.operation)
                    for a in manifest.aggregates
                ]
                if manifest is not None
                else [
                    Aggregate(column_name=c, operation=op)
                    for c, op in (aggregate_columns or {}).items()
                ]
            )
            return Lattice(
                dataframe=df,
                metadata=metadata,
                aggregates=aggregates,
                partition_key=None,
            )

        if dimension_columns is None:
            non_agg = set((aggregate_columns or {}).keys())
            dimension_columns = [
                c for c in df.columns if c not in non_agg and c != "rule_name"
            ]

        dimensions = []
        for col_name in dimension_columns:
            dtype = df.schema[col_name]
            py_type: type = str
            if dtype in (
                pl.Int8,
                pl.Int16,
                pl.Int32,
                pl.Int64,
                pl.UInt8,
                pl.UInt16,
                pl.UInt32,
                pl.UInt64,
            ):
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
    def _fill_sentinels(df: pl.DataFrame, metadata: DimensionsMetadata) -> pl.DataFrame:
        """Restore typed UNKNOWN sentinels in declared scalar dimension columns."""
        exprs = []
        for dim in metadata.dimensions:
            if dim.data_type is DataType.BOOL or dim.match_strategy in {
                MatchStrategy.SET_MEMBERSHIP,
                MatchStrategy.SET_EXCLUSION,
            }:
                continue
            columns = (
                [dim.range_min_field, dim.range_max_field]
                if dim.match_strategy == MatchStrategy.RANGE
                else [dim.resolved_rule_field]
            )
            for column in columns:
                if column in df.columns:
                    value = pl.col(column).cast(_POLARS_TYPES[dim.data_type])
                    exprs.append(
                        value.fill_null(unknown_sentinel_for(dim.data_type)).alias(
                            column
                        )
                    )
        return df.with_columns(exprs) if exprs else df

    @staticmethod
    def _validate_columns(df: pl.DataFrame, metadata: DimensionsMetadata) -> None:
        missing: list[str] = []
        for dim in metadata.dimensions:
            columns = (
                [dim.range_min_field, dim.range_max_field]
                if dim.match_strategy == MatchStrategy.RANGE
                else [dim.resolved_rule_field]
            )
            missing.extend(column for column in columns if column not in df.columns)
        if missing:
            raise ValueError(f"Metadata references columns missing from CSV: {missing}")

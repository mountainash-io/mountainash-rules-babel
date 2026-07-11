from __future__ import annotations

from pathlib import Path

import polars as pl

from mountainash_rules.aggregate import Aggregate
from mountainash_rules.constants import MatchStrategy
from mountainash_rules.dimension import Dimension, DimensionsMetadata
from mountainash_rules.lattice import Lattice


class CsvImporter:
    name: str = "csv"
    file_extensions: list[str] = [".csv"]

    def import_lattice(
        self,
        path: Path,
        *,
        dimension_columns: list[str] | None = None,
        aggregate_columns: dict[str, str] | None = None,
        **options,
    ) -> Lattice:
        df = pl.read_csv(path)

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

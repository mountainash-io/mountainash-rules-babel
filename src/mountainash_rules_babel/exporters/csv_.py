from __future__ import annotations

from pathlib import Path

import polars as pl

from mountainash_utils_rules.lattice import Lattice


class CsvExporter:
    name: str = "csv"
    file_extension: str = ".csv"

    def export(self, lattice: Lattice, path: Path, **options) -> Path:
        path = Path(path)
        df = self._to_polars(lattice)
        df.write_csv(path)
        return path

    def export_bytes(self, lattice: Lattice, **options) -> bytes:
        df = self._to_polars(lattice)
        csv_str = df.write_csv()
        return csv_str.encode("utf-8") if isinstance(csv_str, str) else csv_str

    def _to_polars(self, lattice: Lattice) -> pl.DataFrame:
        combos = lattice.combinations
        if isinstance(combos, pl.DataFrame):
            return combos
        # Try mountainash relation API for ibis/other backends
        try:
            from mountainash.relations import relation

            return relation(combos).to_polars()
        except Exception:
            raise TypeError(f"Cannot convert {type(combos)} to polars DataFrame")

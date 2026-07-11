from __future__ import annotations

from pathlib import Path


from mountainash_rules.lattice import Lattice

from mountainash_rules_babel.exporters.base import lattice_to_polars


class CsvExporter:
    name: str = "csv"
    file_extension: str = ".csv"

    def export(self, lattice: Lattice, path: Path, **options) -> Path:
        path = Path(path)
        df = lattice_to_polars(lattice)
        df.write_csv(path)
        return path

    def export_bytes(self, lattice: Lattice, **options) -> bytes:
        df = lattice_to_polars(lattice)
        csv_str = df.write_csv()
        return csv_str.encode("utf-8") if isinstance(csv_str, str) else csv_str

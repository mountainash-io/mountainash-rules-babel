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

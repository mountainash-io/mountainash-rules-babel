from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from mountainash_utils_rules.lattice import Lattice


@runtime_checkable
class Exporter(Protocol):
    name: str
    file_extension: str

    def export(self, lattice: Lattice, path: Path, **options) -> Path: ...

    def export_bytes(self, lattice: Lattice, **options) -> bytes: ...

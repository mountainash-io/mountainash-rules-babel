from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from mountainash_rules.lattice import Lattice


@runtime_checkable
class Importer(Protocol):
    name: str
    file_extensions: list[str]

    def import_lattice(self, path: Path, **options) -> Lattice: ...

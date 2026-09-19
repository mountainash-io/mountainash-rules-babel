"""Explicit directory transport for complete Rules native snapshots."""

from __future__ import annotations

from pathlib import Path

from mountainash_rules import ExactLimits, Lattice

from mountainash_rules_babel.errors import SchemaContractError


class NativeImporter:
    """Load and validate exact-native snapshots through Rules."""

    name: str = "native"
    file_extensions: list[str] = []

    def import_lattice(self, path: Path, **options) -> Lattice:
        limits = options.get("limits")
        if not isinstance(limits, ExactLimits):
            raise ValueError("Native import requires a complete ExactLimits")
        if path is None:
            raise ValueError("Native import requires a snapshot directory path")
        lattice = Lattice.load(Path(path), limits=limits)
        if lattice.artifact_kind != "exact_cells":
            raise SchemaContractError(
                "Native import requires an exact-native lattice artifact"
            )
        return lattice

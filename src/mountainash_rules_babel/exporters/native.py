"""Explicit directory transport for complete Rules native snapshots."""

from __future__ import annotations

from pathlib import Path

from mountainash_rules import ExactLimits, Lattice

from mountainash_rules_babel.errors import ExportError, SchemaContractError


class NativeExporter:
    """Delegate exact-native publication to Rules without flattening state."""

    name: str = "native"
    file_extension: str = ""

    def export(self, lattice: Lattice, path: Path, **options) -> Path:
        limits = options.get("limits")
        if not isinstance(limits, ExactLimits):
            raise ValueError("Native export requires a complete ExactLimits")
        if path is None:
            raise ValueError("Native export requires a snapshot directory path")
        if lattice.artifact_kind != "exact_cells":
            raise SchemaContractError(
                "Native export requires an exact-native lattice artifact"
            )
        return lattice.save(Path(path), limits=limits)

    def export_bytes(self, lattice: Lattice, **options) -> bytes:
        raise ExportError(
            "Native snapshots require a directory path; byte export is unsupported"
        )

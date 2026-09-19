from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl

from mountainash_rules import ExactLimits, Lattice

from mountainash_rules_babel.errors import SchemaContractError
from mountainash_rules_babel.exporters.base import resolve_lattice
from mountainash_rules_babel.exporters.csv_ import CsvExporter
from mountainash_rules_babel.importers.csv_ import CsvImporter
from mountainash_rules_babel.validators.base import ValidationIssue, ValidationReport


def frames_equivalent(a: pl.DataFrame, b: pl.DataFrame) -> list[str]:
    """Compare two frames modulo column/row order and CSV int widening."""
    if set(a.columns) != set(b.columns):
        only_a = sorted(set(a.columns) - set(b.columns))
        only_b = sorted(set(b.columns) - set(a.columns))
        return [f"column mismatch: only in first {only_a}, only in second {only_b}"]
    if a.height != b.height:
        return [f"row count mismatch: {a.height} vs {b.height}"]
    columns = sorted(a.columns)
    left = a.select(columns)
    right = b.select(columns)
    try:
        right = right.cast(left.schema)
    except pl.exceptions.PolarsError as exc:
        return [f"schema not reconcilable: {exc}"]
    if not left.sort(columns).equals(right.sort(columns)):
        return ["frame values differ after sorting and schema alignment"]
    return []


def _resolved_metadata(metadata) -> dict:
    """Compare public metadata after canonicalizing optional field aliases."""
    payload = metadata.model_dump(mode="json")
    for dimension, encoded in zip(
        metadata.dimensions, payload["dimensions"], strict=True
    ):
        encoded["context_field"] = dimension.resolved_context_field
        encoded["rule_field"] = dimension.resolved_rule_field
    return payload


def _native_report(original: Lattice, restored: Lattice) -> ValidationReport:
    issues: list[ValidationIssue] = []
    for name, before, after in (
        ("artifact_id", original.artifact_id, restored.artifact_id),
        (
            "partition_identity",
            original.partition_identity,
            restored.partition_identity,
        ),
        (
            "metadata",
            _resolved_metadata(original.metadata),
            _resolved_metadata(restored.metadata),
        ),
        ("aggregates", original.aggregates, restored.aggregates),
        ("bindings", original.bindings, restored.bindings),
    ):
        if before != after:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="native_mismatch",
                    message=f"{name} differs after native round trip",
                )
            )
    exact = not issues
    return ValidationReport(
        is_valid=exact,
        issues=issues,
        input_row_count=original.count,
        output_row_count=restored.count,
        exact_match=exact,
    )


class RoundTripValidator:
    name: str = "round_trip"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        fmt = options.get("format", "csv")
        if fmt == "native":
            limits = options.get("limits")
            if not isinstance(limits, ExactLimits):
                raise ValueError(
                    "Native round-trip validation requires a complete ExactLimits"
                )
            if lattice.artifact_kind != "exact_cells":
                raise SchemaContractError(
                    "Native round-trip validation requires an exact-native lattice artifact"
                )
            snapshot = options.get("path")
            if snapshot is not None:
                restored = Lattice.load(Path(snapshot), limits=limits)
                return _native_report(lattice, restored)
            workdir = options.get("workdir")
            with tempfile.TemporaryDirectory(dir=workdir) as fallback:
                snapshot = lattice.save(Path(fallback) / "round_trip", limits=limits)
                restored = Lattice.load(snapshot, limits=limits)
                return _native_report(lattice, restored)

        if fmt != "csv":
            return ValidationReport(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        severity="warning",
                        category="not_implemented",
                        message=f"round_trip validation for format {fmt!r} is not supported",
                    )
                ],
            )
        if lattice.artifact_kind is not None:
            raise SchemaContractError(
                "CSV round-trip validation accepts only flat values; exact-native "
                "lattices require format='native'"
            )

        workdir = options.get("workdir")
        with tempfile.TemporaryDirectory(dir=workdir) as fallback:
            path = Path(fallback) / "round_trip.csv"
            CsvExporter().export(lattice, path)
            imported = CsvImporter().import_lattice(path)

        view = resolve_lattice(lattice)
        imported_df = pl.DataFrame(imported.combinations)
        issues: list[ValidationIssue] = []
        for difference in frames_equivalent(imported_df, view.df):
            issues.append(
                ValidationIssue(
                    severity="error", category="frame_mismatch", message=difference
                )
            )
        if imported.metadata != lattice.metadata:
            differing = [
                field
                for field in type(lattice.metadata).model_fields
                if getattr(imported.metadata, field) != getattr(lattice.metadata, field)
            ]
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="metadata_mismatch",
                    message=f"metadata fields differ after round trip: {differing}",
                )
            )

        exact = not issues
        return ValidationReport(
            is_valid=exact,
            issues=issues,
            input_row_count=view.df.height,
            output_row_count=imported_df.height,
            exact_match=exact,
        )

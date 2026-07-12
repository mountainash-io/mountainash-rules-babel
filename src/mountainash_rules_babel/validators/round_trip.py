from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl

from mountainash_rules.lattice import Lattice

from mountainash_rules_babel.exporters.base import resolve_lattice
from mountainash_rules_babel.exporters.csv_ import CsvExporter
from mountainash_rules_babel.importers.csv_ import CsvImporter
from mountainash_rules_babel.validators.base import ValidationIssue, ValidationReport


def frames_equivalent(a: pl.DataFrame, b: pl.DataFrame) -> list[str]:
    """Compare two frames modulo column/row order and CSV int widening.

    Returns human-readable differences; empty list means equivalent.
    """
    if set(a.columns) != set(b.columns):
        only_a = sorted(set(a.columns) - set(b.columns))
        only_b = sorted(set(b.columns) - set(a.columns))
        return [f"column mismatch: only in first {only_a}, only in second {only_b}"]
    if a.height != b.height:
        return [f"row count mismatch: {a.height} vs {b.height}"]
    cols = sorted(a.columns)
    left = a.select(cols)
    right = b.select(cols)
    try:
        right = right.cast(left.schema)
    except pl.exceptions.PolarsError as exc:
        return [f"schema not reconcilable: {exc}"]
    if not left.sort(cols).equals(right.sort(cols)):
        return ["frame values differ after sorting and schema alignment"]
    return []


class RoundTripValidator:
    name: str = "round_trip"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        fmt = options.get("format", "csv")
        if fmt != "csv":
            return ValidationReport(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        severity="warning",
                        category="not_implemented",
                        message=f"round_trip validation for format {fmt!r} "
                        f"is not supported; only csv round-trips losslessly",
                    )
                ],
            )

        workdir = options.get("workdir")
        with tempfile.TemporaryDirectory() as fallback:
            path = Path(workdir or fallback) / "round_trip.csv"
            CsvExporter().export(lattice, path)
            imported = CsvImporter().import_lattice(path)

        view = resolve_lattice(lattice)
        imported_df = pl.DataFrame(imported.combinations)
        issues: list[ValidationIssue] = []
        for diff in frames_equivalent(imported_df, view.df):
            issues.append(
                ValidationIssue(severity="error", category="frame_mismatch",
                                message=diff)
            )
        if imported.metadata != lattice.metadata:
            differing = [
                f
                for f in type(lattice.metadata).model_fields
                if getattr(imported.metadata, f) != getattr(lattice.metadata, f)
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

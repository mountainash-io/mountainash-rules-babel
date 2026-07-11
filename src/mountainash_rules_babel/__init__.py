"""Mountain Ash Rules Babel — translate decision logic between formats."""

from __future__ import annotations

import typing as t
from pathlib import Path

from mountainash_rules_babel.__version__ import __version__
from mountainash_rules_babel.errors import FormatNotFoundError
from mountainash_rules_babel.registry import registry
from mountainash_rules_babel.validators.base import ValidationIssue, ValidationReport

if t.TYPE_CHECKING:
    from mountainash_rules.aggregate import Aggregate
    from mountainash_rules.dimension import DimensionsMetadata
    from mountainash_rules.lattice import Lattice

    from mountainash_rules_babel.decomposers.base import DecompositionResult, Fragment


def export_lattice(
    lattice: Lattice,
    format: str,
    path: Path | str | None = None,
    validate: bool = False,
    **options: t.Any,
) -> Path | bytes:
    exporter = registry.get_exporter(format)
    if path is not None:
        result: Path | bytes = exporter.export(lattice, Path(path), **options)
    else:
        result = exporter.export_bytes(lattice, **options)

    if validate:
        from mountainash_rules_babel.errors import ValidationError

        report = _run_validators(lattice, ["round_trip"])
        if not report.is_valid and report.errors:
            raise ValidationError("Validation failed after export", report=report)

    return result


def import_lattice(
    path: Path | str,
    format: str | None = None,
    **options: t.Any,
) -> Lattice:
    path = Path(path)
    if format is None:
        importer = registry.get_importer_for_extension(path.suffix)
    else:
        importer = registry.get_importer(format)
    return importer.import_lattice(path, **options)


def decompose(
    lattice: Lattice,
    strategy: str = "hyfd",
    **options: t.Any,
) -> DecompositionResult:
    decomposer = registry.get_decomposer(strategy)
    return decomposer.decompose(lattice, **options)


def validate(
    lattice: Lattice,
    checks: list[str] | None = None,
    **options: t.Any,
) -> ValidationReport:
    return _run_validators(lattice, checks, **options)


def compose(
    fragments: list[Fragment],
    metadata: DimensionsMetadata | None = None,
    aggregates: list[Aggregate] | None = None,
    **options: t.Any,
) -> Lattice:
    raise NotImplementedError(
        "compose() requires the fragment-to-engine contract (spec Section 6.1). "
        "This will be implemented when decomposition is available."
    )


def round_trip(
    path: Path | str,
    input_format: str | None = None,
    output_format: str | None = None,
    **options: t.Any,
) -> t.Any:
    raise NotImplementedError(
        "round_trip() requires compose() and decompose(). "
        "This will be implemented when decomposition is available."
    )


def _run_validators(
    lattice: Lattice,
    checks: list[str] | None = None,
    **options: t.Any,
) -> ValidationReport:
    if checks is None:
        validator_names = registry.list_validators()
    else:
        validator_names = checks

    all_issues: list[ValidationIssue] = []
    for name in validator_names:
        validator = registry.get_validator(name)
        report = validator.validate(lattice, **options)
        all_issues.extend(report.issues)

    is_valid = all(issue.severity != "error" for issue in all_issues)
    has_not_implemented = any(issue.category == "not_implemented" for issue in all_issues)
    if has_not_implemented:
        is_valid = False

    return ValidationReport(is_valid=is_valid, issues=all_issues)


__all__ = (
    "__version__",
    "compose",
    "decompose",
    "export_lattice",
    "import_lattice",
    "round_trip",
    "validate",
)

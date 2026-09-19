import tempfile
from pathlib import Path

import pytest
from mountainash_rules_babel import export_lattice, import_lattice, validate
from mountainash_rules_babel.errors import ValidationError
from mountainash_rules_babel.validators.base import ValidationReport

FIXTURES = Path(__file__).parent / "fixtures"


def test_import_lattice_csv():
    lattice = import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
        aggregate_columns={"price": "sum"},
    )
    assert lattice.count == 3


def test_import_lattice_infers_format():
    lattice = import_lattice(
        FIXTURES / "pricing_3row.csv",
        dimension_columns=["country", "product"],
    )
    assert lattice.count == 3


def test_export_lattice_csv_to_file():
    lattice = import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        result = export_lattice(lattice, "csv", path=Path(tmpdir) / "out.csv")
        assert isinstance(result, Path)
        assert result.exists()


def test_export_lattice_csv_to_bytes():
    lattice = import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
    )
    result = export_lattice(lattice, "csv")
    assert isinstance(result, bytes)
    assert b"country" in result


def test_export_lattice_dmn_to_bytes():
    lattice = import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
    )
    result = export_lattice(lattice, "dmn")
    assert isinstance(result, bytes)
    assert b"decisionTable" in result


def test_export_validate_rejects_unimplemented_dmn_round_trip(tmp_path):
    lattice = import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
    )

    with pytest.raises(ValidationError) as failure:
        export_lattice(lattice, "dmn", path=tmp_path / "rules.dmn", validate=True)

    assert failure.value.report is not None
    assert not failure.value.report.is_valid


def test_export_native_forwards_format_and_limits_to_round_trip_validation(tmp_path):
    from tests.exact_fixture import build_exact_lattice

    _, lattice, _, explicit_limits = build_exact_lattice()

    snapshot = export_lattice(
        lattice,
        "native",
        path=tmp_path / "snapshot",
        limits=explicit_limits,
        validate=True,
    )

    assert snapshot.is_dir()


def test_validate_returns_fail_closed_report():
    lattice = import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
    )
    report = validate(lattice)
    assert isinstance(report, ValidationReport)
    assert report.is_valid is False
    assert len(report.warnings) > 0
    assert all(w.category == "not_implemented" for w in report.warnings)


def test_serving_names_importable_from_root():
    from mountainash_rules_babel import AggregateSpec, LatticeManifest

    assert hasattr(LatticeManifest, "from_yaml_file")
    assert hasattr(LatticeManifest, "for_lattice")
    assert AggregateSpec(column_name="discount").operation == "sum"


def test_names_in_dunder_all():
    import mountainash_rules_babel as babel

    assert "LatticeManifest" in babel.__all__
    assert "AggregateSpec" in babel.__all__
    assert list(babel.__all__) == sorted(babel.__all__, key=str.lower)

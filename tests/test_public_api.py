import tempfile
from pathlib import Path

from mountainash_rules_babel import export_lattice, import_lattice, validate
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

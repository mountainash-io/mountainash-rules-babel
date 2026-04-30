import tempfile
from pathlib import Path

from typer.testing import CliRunner

from mountainash_rules_babel.cli.main import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_formats_command():
    result = runner.invoke(app, ["formats"])
    assert result.exit_code == 0
    assert "csv" in result.stdout


def test_export_csv():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "out.csv"
        result = runner.invoke(app, [
            "export",
            "--format", "csv",
            "--input", str(FIXTURES / "pricing_3row.csv"),
            "--output", str(out),
            "--dim", "country",
            "--dim", "product",
        ])
        assert result.exit_code == 0, result.stdout
        assert out.exists()


def test_export_dmn():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "out.dmn"
        result = runner.invoke(app, [
            "export",
            "--format", "dmn",
            "--input", str(FIXTURES / "pricing_3row.csv"),
            "--output", str(out),
            "--dim", "country",
            "--dim", "product",
        ])
        assert result.exit_code == 0, result.stdout
        assert out.exists()
        assert b"decisionTable" in out.read_bytes()


def test_import_csv():
    result = runner.invoke(app, [
        "import",
        "--input", str(FIXTURES / "pricing_3row.csv"),
        "--dim", "country",
        "--dim", "product",
    ])
    assert result.exit_code == 0
    assert "Imported 3 rows" in result.stdout
    assert "country" in result.stdout


def test_validate_csv():
    result = runner.invoke(app, [
        "validate",
        "--input", str(FIXTURES / "pricing_3row.csv"),
        "--dim", "country",
        "--dim", "product",
    ])
    assert result.exit_code == 0
    assert "Valid: False" in result.stdout
    assert "not_implemented" in result.stdout

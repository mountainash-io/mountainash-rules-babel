import tempfile
from pathlib import Path

import polars as pl

import mountainash_rules_babel as babel

FIXTURES = Path(__file__).parent / "fixtures"


def test_csv_round_trip_preserves_data():
    """Import CSV -> export CSV -> re-import -> compare. Row-level exactness."""
    lattice = babel.import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
        aggregate_columns={"price": "sum"},
    )
    assert lattice.count == 3

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "round_trip.csv"
        babel.export_lattice(lattice, "csv", path=out_path)

        lattice2 = babel.import_lattice(
            out_path,
            format="csv",
            dimension_columns=["country", "product"],
            aggregate_columns={"price": "sum"},
        )

    assert lattice2.count == lattice.count

    df1 = lattice.combinations
    df2 = lattice2.combinations
    if isinstance(df1, pl.DataFrame) and isinstance(df2, pl.DataFrame):
        df1_sorted = df1.sort(["country", "product"])
        df2_sorted = df2.sort(["country", "product"])
        assert df1_sorted.equals(df2_sorted)


def test_csv_to_dmn_export():
    """Import CSV -> export DMN -> verify DMN has correct structure."""
    lattice = babel.import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
    )

    dmn_bytes = babel.export_lattice(lattice, "dmn")
    assert isinstance(dmn_bytes, bytes)
    assert b"decisionTable" in dmn_bytes
    assert b"country" in dmn_bytes
    assert b"product" in dmn_bytes


def test_csv_to_dmn_file_export():
    """Import CSV -> export DMN to file -> verify file is valid XML."""
    from lxml import etree

    lattice = babel.import_lattice(
        FIXTURES / "pricing_3row.csv",
        format="csv",
        dimension_columns=["country", "product"],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "pricing.dmn"
        result = babel.export_lattice(lattice, "dmn", path=out_path)
        assert result.exists()

        tree = etree.parse(str(out_path))
        root = tree.getroot()
        ns = {"dmn": "https://www.omg.org/spec/DMN/20191111/MODEL/"}
        rules = root.findall(".//dmn:rule", ns)
        assert len(rules) == 3

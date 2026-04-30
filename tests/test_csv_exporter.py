import tempfile
from pathlib import Path

import polars as pl
from mountainash_utils_rules.aggregate import Aggregate
from mountainash_utils_rules.constants import MatchStrategy
from mountainash_utils_rules.dimension import Dimension, DimensionsMetadata
from mountainash_utils_rules.lattice import Lattice

from mountainash_rules_babel.exporters.csv_ import CsvExporter


def _make_lattice() -> Lattice:
    metadata = DimensionsMetadata(
        dimensions=[
            Dimension(dimension_name="country", match_strategy=MatchStrategy.EXACT, data_type=str),
            Dimension(dimension_name="product", match_strategy=MatchStrategy.EXACT, data_type=str),
        ]
    )
    df = pl.DataFrame({
        "country": ["AU", "NZ", "AU"],
        "product": ["widget", "widget", "gadget"],
        "price": [100, 90, 150],
    })
    return Lattice(
        dataframe=df,
        metadata=metadata,
        aggregates=[Aggregate(column_name="price", operation="sum")],
        partition_key=None,
    )


def test_csv_export_to_file():
    exporter = CsvExporter()
    lattice = _make_lattice()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "output.csv"
        result = exporter.export(lattice, out_path)
        assert result == out_path
        assert out_path.exists()

        roundtrip = pl.read_csv(out_path)
        assert roundtrip.shape == (3, 3)
        assert set(roundtrip.columns) == {"country", "product", "price"}


def test_csv_export_to_bytes():
    exporter = CsvExporter()
    lattice = _make_lattice()
    data = exporter.export_bytes(lattice)
    assert isinstance(data, bytes)
    assert b"country" in data
    assert b"AU" in data


def test_csv_exporter_protocol_fields():
    exporter = CsvExporter()
    assert exporter.name == "csv"
    assert exporter.file_extension == ".csv"

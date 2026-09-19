import tempfile
from pathlib import Path

import polars as pl
import pytest
from mountainash_rules import (
    Aggregate,
    Dimension,
    DimensionsMetadata,
    Lattice,
    MatchStrategy,
)

from mountainash_rules_babel.exporters.csv_ import CsvExporter


def _make_lattice() -> Lattice:
    metadata = DimensionsMetadata(
        dimensions=[
            Dimension(
                dimension_name="country",
                match_strategy=MatchStrategy.EXACT,
                data_type=str,
            ),
            Dimension(
                dimension_name="product",
                match_strategy=MatchStrategy.EXACT,
                data_type=str,
            ),
        ]
    )
    df = pl.DataFrame(
        {
            "country": ["AU", "NZ", "AU"],
            "product": ["widget", "widget", "gadget"],
            "price": [100, 90, 150],
        }
    )
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


@pytest.mark.parametrize("legacy_sidecar", [False, True])
def test_csv_round_trip_preserves_output_sentinel_but_blanks_dimension_sentinel(
    tmp_path, legacy_sidecar
):
    from mountainash_rules import DataType, UNKNOWN_NUMERIC
    from mountainash_rules_babel.importers.csv_ import CsvImporter

    metadata = DimensionsMetadata(
        dimensions=[
            Dimension(
                dimension_name="threshold",
                match_strategy=MatchStrategy.RANGE,
                data_type=DataType.INT,
                range_min_field="threshold_min",
                range_max_field="threshold_max",
            ),
        ]
    )
    lattice = Lattice(
        dataframe=pl.DataFrame(
            {
                "threshold_min": [UNKNOWN_NUMERIC],
                "threshold_max": [10],
                "amount": [UNKNOWN_NUMERIC],
            }
        ),
        metadata=metadata,
        aggregates=[Aggregate(column_name="amount", operation="sum")],
        partition_key=None,
    )
    path = CsvExporter().export(lattice, tmp_path / "sentinel.csv")
    if legacy_sidecar:
        import yaml

        sidecar = path.with_suffix(".manifest.yaml")
        payload = yaml.safe_load(sidecar.read_text())
        payload.pop("fidelity")
        sidecar.write_text(yaml.safe_dump(payload, sort_keys=False))

    assert f",{UNKNOWN_NUMERIC}\n" in path.read_text()
    imported = CsvImporter().import_lattice(path)
    values = pl.DataFrame(imported.combinations).row(0, named=True)
    assert values["threshold_min"] == UNKNOWN_NUMERIC
    assert values["amount"] == UNKNOWN_NUMERIC


def test_csv_round_trip_keeps_boolean_dimension_null_as_wildcard(tmp_path):
    from mountainash_rules import DataType
    from mountainash_rules_babel.importers.csv_ import CsvImporter

    metadata = DimensionsMetadata(
        dimensions=[
            Dimension(
                dimension_name="approved",
                match_strategy=MatchStrategy.EXACT,
                data_type=DataType.BOOL,
            )
        ]
    )
    lattice = Lattice(
        dataframe=pl.DataFrame({"approved": [None, True], "amount": [1, 2]}),
        metadata=metadata,
        aggregates=[Aggregate(column_name="amount", operation="sum")],
        partition_key=None,
    )

    path = CsvExporter().export(lattice, tmp_path / "boolean.csv")
    imported = CsvImporter().import_lattice(path)

    assert pl.DataFrame(imported.combinations)["approved"].to_list() == [None, True]

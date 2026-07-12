from pathlib import Path

from mountainash_rules_babel.importers.csv_ import CsvImporter

FIXTURES = Path(__file__).parent / "fixtures"


def test_csv_import_creates_lattice():
    importer = CsvImporter()
    lattice = importer.import_lattice(
        FIXTURES / "pricing_3row.csv",
        dimension_columns=["country", "product"],
        aggregate_columns={"price": "sum"},
    )
    assert lattice.count == 3
    assert len(lattice.metadata.dimensions) == 2
    assert lattice.metadata.dimensions[0].dimension_name == "country"
    assert lattice.metadata.dimensions[1].dimension_name == "product"


def test_csv_import_infers_match_strategy():
    importer = CsvImporter()
    lattice = importer.import_lattice(
        FIXTURES / "pricing_3row.csv",
        dimension_columns=["country", "product"],
    )
    from mountainash_rules.constants import MatchStrategy

    for dim in lattice.metadata.dimensions:
        assert dim.match_strategy == MatchStrategy.EXACT


def test_csv_importer_protocol_fields():
    importer = CsvImporter()
    assert importer.name == "csv"
    assert ".csv" in importer.file_extensions


def test_import_with_explicit_metadata_produces_range_dimension(tmp_path):
    import polars as pl
    from mountainash_rules.constants import DataType, MatchStrategy
    from mountainash_rules.dimension import Dimension, DimensionsMetadata
    from mountainash_rules_babel.importers.csv_ import CsvImporter

    csv = tmp_path / "rules.csv"
    pl.DataFrame({
        "rule_name": ["r1"], "amt_min": [0], "amt_max": [100],
    }).write_csv(csv)
    md = DimensionsMetadata(dimensions=[
        Dimension(
            dimension_name="amount", match_strategy=MatchStrategy.RANGE,
            data_type=DataType.INT,
            range_min_field="amt_min", range_max_field="amt_max",
        ),
    ])
    lattice = CsvImporter().import_lattice(csv, metadata=md)
    assert lattice.metadata.dimensions[0].match_strategy is MatchStrategy.RANGE


def test_import_with_metadata_missing_range_column_raises(tmp_path):
    import polars as pl
    import pytest
    from mountainash_rules.constants import DataType, MatchStrategy
    from mountainash_rules.dimension import Dimension, DimensionsMetadata
    from mountainash_rules_babel.importers.csv_ import CsvImporter

    csv = tmp_path / "rules.csv"
    pl.DataFrame({"rule_name": ["r1"], "amt_min": [0]}).write_csv(csv)
    md = DimensionsMetadata(dimensions=[
        Dimension(
            dimension_name="amount", match_strategy=MatchStrategy.RANGE,
            data_type=DataType.INT,
            range_min_field="amt_min", range_max_field="amt_max",
        ),
    ])
    with pytest.raises(ValueError, match="amt_max"):
        CsvImporter().import_lattice(csv, metadata=md)


def test_import_with_metadata_yaml_path(tmp_path):
    import polars as pl
    from mountainash_rules.dimension import Dimension, DimensionsMetadata
    from mountainash_rules_babel.importers.csv_ import CsvImporter

    csv = tmp_path / "rules.csv"
    pl.DataFrame({"rule_name": ["r1"], "region": ["AU"]}).write_csv(csv)
    md = DimensionsMetadata(dimensions=[Dimension(dimension_name="region")])
    yaml_path = md.to_yaml_file(tmp_path / "md.yaml")
    lattice = CsvImporter().import_lattice(csv, metadata=yaml_path)
    assert lattice.metadata == md

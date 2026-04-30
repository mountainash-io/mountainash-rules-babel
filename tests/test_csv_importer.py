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
    from mountainash_utils_rules.constants import MatchStrategy

    for dim in lattice.metadata.dimensions:
        assert dim.match_strategy == MatchStrategy.EXACT


def test_csv_importer_protocol_fields():
    importer = CsvImporter()
    assert importer.name == "csv"
    assert ".csv" in importer.file_extensions

from pathlib import Path

import polars as pl
from mountainash_rules.aggregate import Aggregate
from mountainash_rules.constants import MatchStrategy
from mountainash_rules.dimension import Dimension, DimensionsMetadata
from mountainash_rules.lattice import Lattice

from mountainash_rules_babel.decomposers.base import Decomposer, DecompositionResult, Fragment
from mountainash_rules_babel.exporters.base import Exporter
from mountainash_rules_babel.importers.base import Importer
from mountainash_rules_babel.validators.base import ValidationReport, Validator


def _make_lattice() -> Lattice:
    metadata = DimensionsMetadata(
        dimensions=[
            Dimension(dimension_name="country", match_strategy=MatchStrategy.EXACT, data_type=str),
        ]
    )
    df = pl.DataFrame({"country": ["AU", "NZ"], "price": [100, 90]})
    return Lattice(dataframe=df, metadata=metadata, aggregates=[], partition_key=None)


class FakeExporter:
    name = "fake"
    file_extension = ".fake"

    def export(self, lattice: Lattice, path: Path, **options) -> Path:
        path.write_text("fake")
        return path

    def export_bytes(self, lattice: Lattice, **options) -> bytes:
        return b"fake"


class FakeImporter:
    name = "fake"
    file_extensions = [".fake"]

    def import_lattice(self, path: Path, **options) -> Lattice:
        return _make_lattice()


class FakeDecomposer:
    name = "fake"

    def decompose(self, lattice: Lattice, **options) -> DecompositionResult:
        return DecompositionResult(
            fragments=[],
            metadata=lattice.metadata,
            aggregates=lattice.aggregates,
            original_row_count=lattice.count,
            fragment_count=0,
            dimension_groups=[],
            validation=None,
        )


class FakeValidator:
    name = "fake"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        return ValidationReport(is_valid=True, issues=[])


def test_exporter_protocol():
    assert isinstance(FakeExporter(), Exporter)


def test_importer_protocol():
    assert isinstance(FakeImporter(), Importer)


def test_decomposer_protocol():
    assert isinstance(FakeDecomposer(), Decomposer)


def test_validator_protocol():
    assert isinstance(FakeValidator(), Validator)


def test_non_conforming_class_is_not_exporter():
    class Bad:
        pass

    assert not isinstance(Bad(), Exporter)

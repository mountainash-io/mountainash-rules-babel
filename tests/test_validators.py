import polars as pl
from mountainash_utils_rules.constants import MatchStrategy
from mountainash_utils_rules.dimension import Dimension, DimensionsMetadata
from mountainash_utils_rules.lattice import Lattice

from mountainash_rules_babel.validators.round_trip import RoundTripValidator
from mountainash_rules_babel.validators.conflicts import ConflictsValidator
from mountainash_rules_babel.validators.coverage import CoverageValidator
from mountainash_rules_babel.validators.orphans import OrphansValidator


def _make_lattice() -> Lattice:
    metadata = DimensionsMetadata(
        dimensions=[
            Dimension(dimension_name="country", match_strategy=MatchStrategy.EXACT, data_type=str),
        ]
    )
    return Lattice(
        dataframe=pl.DataFrame({"country": ["AU"]}),
        metadata=metadata,
        aggregates=[],
        partition_key=None,
    )


def test_round_trip_stub_is_fail_closed():
    v = RoundTripValidator()
    report = v.validate(_make_lattice())
    assert report.is_valid is False
    assert len(report.warnings) == 1
    assert report.warnings[0].category == "not_implemented"
    assert "round_trip" in report.warnings[0].message


def test_conflicts_stub_is_fail_closed():
    v = ConflictsValidator()
    report = v.validate(_make_lattice())
    assert report.is_valid is False
    assert report.warnings[0].category == "not_implemented"


def test_coverage_stub_is_fail_closed():
    v = CoverageValidator()
    report = v.validate(_make_lattice())
    assert report.is_valid is False
    assert report.warnings[0].category == "not_implemented"


def test_orphans_stub_is_fail_closed():
    v = OrphansValidator()
    report = v.validate(_make_lattice())
    assert report.is_valid is False
    assert report.warnings[0].category == "not_implemented"

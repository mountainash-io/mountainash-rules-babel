"""Tests for the flat/composed lattice schema contract."""

import polars as pl
import pytest

from mountainash_rules.aggregate import Aggregate
from mountainash_rules.accumulator_engine import AccumulatorEngine
from mountainash_rules.constants import (
    UNKNOWN,
    UNKNOWN_NUMERIC,
    MatchStrategy,
)
from mountainash_rules.dimension import Dimension, DimensionsMetadata
from mountainash_rules.lattice import Lattice

from mountainash_rules_babel.errors import SchemaContractError
from mountainash_rules_babel.manifest import LatticeManifest


def _metadata():
    return DimensionsMetadata(dimensions=[
        Dimension(dimension_name="region"),
        Dimension(
            dimension_name="lvr", match_strategy=MatchStrategy.RANGE,
            data_type=int, range_min_field="lvr_min", range_max_field="lvr_max",
        ),
    ])


def _composed_lattice():
    engine = AccumulatorEngine(
        dimension_metadata=_metadata(),
        aggregates=[Aggregate(column_name="margin")],
    )
    rules = pl.DataFrame({
        "rule_name": ["R1", "R2"],
        "region": ["AU", UNKNOWN],
        "lvr_min": [60, 70],
        "lvr_max": [80, 90],
        "margin": [-0.10, -0.05],
    })
    return engine.build(rules)


def _flat_lattice():
    return Lattice(
        dataframe=pl.DataFrame({
            "rule_name": ["R1"], "region": ["AU"],
            "lvr_min": [60], "lvr_max": [80], "margin": [-0.10],
        }),
        metadata=_metadata(),
        aggregates=[Aggregate(column_name="margin")],
        partition_key=None,
    )


class TestLatticeManifest:
    def test_round_trip(self, tmp_path):
        manifest = LatticeManifest.for_lattice(_flat_lattice())
        p = manifest.to_yaml_file(tmp_path / "x.manifest.yaml")
        loaded = LatticeManifest.from_yaml_file(p)
        assert loaded == manifest
        assert loaded.dimensions == _metadata()
        assert loaded.aggregates[0].column_name == "margin"

    def test_error_type_exists(self):
        assert issubclass(SchemaContractError, Exception)

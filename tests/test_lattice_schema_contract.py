"""Tests for the inspection-only flat lattice schema contract."""

import yaml

import polars as pl
import pytest
from mountainash_rules import Aggregate, Dimension, DimensionsMetadata, Lattice, MatchStrategy

from mountainash_rules_babel.exporters.base import resolve_lattice
from mountainash_rules_babel.manifest import AggregateSpec, LatticeManifest


def _metadata() -> DimensionsMetadata:
    return DimensionsMetadata(
        dimensions=[
            Dimension(dimension_name="region"),
            Dimension(
                dimension_name="lvr",
                match_strategy=MatchStrategy.RANGE,
                data_type=int,
                range_min_field="lvr_min",
                range_max_field="lvr_max",
            ),
        ]
    )


def _flat_lattice() -> Lattice:
    return Lattice(
        dataframe=pl.DataFrame(
            {
                "rule_name": ["R1"],
                "region": ["AU"],
                "lvr_min": [60],
                "lvr_max": [80],
                "margin": [-0.10],
            }
        ),
        metadata=_metadata(),
        aggregates=[Aggregate(column_name="margin")],
        partition_key=None,
    )


class TestFlatManifestFidelity:
    def test_new_sidecars_have_only_flat_fidelity_metadata(self):
        manifest = LatticeManifest.for_lattice(_flat_lattice())

        assert manifest.model_dump(mode="json") == {
            "fidelity": "flat_values",
            "dimensions": _metadata().model_dump(mode="json"),
            "aggregates": [{"column_name": "margin", "operation": "sum"}],
        }

    def test_legacy_sidecar_is_accepted_for_flat_inspection(self):
        legacy = {
            "dimensions": _metadata().model_dump(mode="json"),
            "aggregates": [{"column_name": "margin", "operation": "sum"}],
        }

        manifest = LatticeManifest.from_yaml(yaml.safe_dump(legacy))

        assert manifest.fidelity == "flat_values"
        assert manifest.dimensions == _metadata()
        assert manifest.aggregates == [AggregateSpec(column_name="margin")]

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "fidelity": "native",
                "dimensions": _metadata().model_dump(mode="json"),
                "aggregates": [],
            },
            {
                "fidelity": "flat_values",
                "artifact_kind": "exact_cells",
                "dimensions": _metadata().model_dump(mode="json"),
                "aggregates": [],
            },
            {
                "fidelity": "flat_values",
                "dimensions": _metadata().model_dump(mode="json"),
                "aggregates": [],
                "unexpected": True,
            },
        ],
    )
    def test_rejects_unknown_or_native_sidecar_declarations(self, payload):
        with pytest.raises(ValueError):
            LatticeManifest.from_yaml(yaml.safe_dump(payload))


def test_flat_resolver_preserves_declared_values_and_outputs():
    view = resolve_lattice(_flat_lattice())

    assert view.df.columns == ["rule_name", "region", "lvr_min", "lvr_max", "margin"]
    assert view.output_columns == ["margin"]

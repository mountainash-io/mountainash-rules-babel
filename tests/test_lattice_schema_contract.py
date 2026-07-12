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


from mountainash_rules_babel.exporters.base import resolve_lattice


class TestResolveLattice:
    def test_composed_values_are_coalesced_under_flat_names(self):
        view = resolve_lattice(_composed_lattice())
        assert view.is_composed is True
        # co_lvr_min renamed to lvr_min; the coalesced pair row [70, 80]
        # must exist (the R2 singleton [70, 90] also legitimately survives
        # the frontier under its own fingerprint)
        pairs = view.df.filter(pl.col("lvr_min") == 70)
        assert 80 in pairs["lvr_max"].to_list()

    def test_composed_drops_stale_columns(self):
        view = resolve_lattice(_composed_lattice())
        assert "rule_name" in view.dropped_stale
        assert not any(c.startswith("co_") for c in view.df.columns)
        assert not any(c.startswith("__") for c in view.df.columns)

    def test_composed_output_columns_are_renamed_aggregates_only(self):
        view = resolve_lattice(_composed_lattice())
        assert view.output_columns == ["margin"]
        assert "margin" in view.df.columns

    def test_composed_tracking_split_out(self):
        view = resolve_lattice(_composed_lattice(), include_tracking=True)
        assert view.tracking is not None
        assert "__prime_product" in view.tracking.columns

    def test_flat_passthrough(self):
        view = resolve_lattice(_flat_lattice())
        assert view.is_composed is False
        assert view.output_columns == ["margin"]
        assert view.dropped_stale == []

    def test_flat_with_tracking_columns_is_mixed_shape(self):
        bad = Lattice(
            dataframe=pl.DataFrame({
                "rule_name": ["r"], "region": ["AU"],
                "lvr_min": [0], "lvr_max": [1], "margin": [0.0],
                "__level": [1],
            }),
            metadata=_metadata(), aggregates=[], partition_key=None,
        )
        with pytest.raises(SchemaContractError, match="__level"):
            resolve_lattice(bad)

    def test_flat_user_co_column_is_legal(self):
        ok = Lattice(
            dataframe=pl.DataFrame({
                "rule_name": ["r"], "region": ["AU"],
                "lvr_min": [0], "lvr_max": [1], "margin": [0.0],
                "co_brand": ["x"],
            }),
            metadata=_metadata(), aggregates=[], partition_key=None,
        )
        view = resolve_lattice(ok)
        assert "co_brand" in view.df.columns


from mountainash_rules_babel.exporters.csv_ import CsvExporter


class TestCsvExport:
    def test_composed_export_has_flat_names_no_tracking(self, tmp_path):
        p = CsvExporter().export(_composed_lattice(), tmp_path / "out.csv")
        df = pl.read_csv(p)
        assert "lvr_min" in df.columns and "margin" in df.columns
        assert not any(c.startswith(("co_", "__")) for c in df.columns)

    def test_sentinels_written_as_empty_cells(self, tmp_path):
        p = CsvExporter().export(_composed_lattice(), tmp_path / "out.csv")
        text = p.read_text()
        assert str(UNKNOWN_NUMERIC) not in text
        assert UNKNOWN not in text

    def test_include_tracking_appends_columns(self, tmp_path):
        p = CsvExporter().export(
            _composed_lattice(), tmp_path / "out.csv", include_tracking=True
        )
        assert "__prime_product" in pl.read_csv(p).columns

    def test_manifest_sidecar_written(self, tmp_path):
        CsvExporter().export(_composed_lattice(), tmp_path / "out.csv")
        manifest = LatticeManifest.from_yaml_file(tmp_path / "out.manifest.yaml")
        assert manifest.dimensions == _metadata()
        assert manifest.aggregates[0].column_name == "margin"


import warnings

from mountainash_rules_babel.importers.csv_ import CsvImporter


class TestCsvImportContract:
    def _export(self, tmp_path, **kwargs):
        return CsvExporter().export(
            _composed_lattice(), tmp_path / "out.csv", **kwargs
        )

    def test_sidecar_autoloaded(self, tmp_path):
        p = self._export(tmp_path)
        lattice = CsvImporter().import_lattice(p)
        assert lattice.metadata == _metadata()
        assert lattice.aggregates[0].column_name == "margin"

    def test_empty_cells_become_typed_sentinels(self, tmp_path):
        p = self._export(tmp_path)
        lattice = CsvImporter().import_lattice(p)
        df = pl.DataFrame(lattice.combinations)
        # R2's region was <NA> -> exported empty -> re-imported as UNKNOWN
        assert UNKNOWN in df["region"].to_list()
        assert df["lvr_min"].null_count() == 0
        assert df["lvr_max"].null_count() == 0

    def test_tracking_columns_stripped_with_warning(self, tmp_path):
        p = self._export(tmp_path, include_tracking=True)
        with pytest.warns(UserWarning, match="__prime_product"):
            lattice = CsvImporter().import_lattice(p)
        assert lattice.is_composed is False

    def test_import_is_always_flat(self, tmp_path):
        p = self._export(tmp_path)
        assert CsvImporter().import_lattice(p).is_composed is False

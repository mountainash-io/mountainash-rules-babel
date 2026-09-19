"""Native snapshot transport uses the bounded public Rules API unchanged."""

from importlib import import_module

import polars as pl
import pytest
from mountainash_rules import (
    Dimension,
    DimensionsMetadata,
    InvalidContextError,
    Lattice,
)

import mountainash_rules_babel as babel

from mountainash_rules_babel.errors import ExportError, SchemaContractError
from tests.exact_fixture import build_exact_lattice, limits


def _plugins():
    exporter = import_module("mountainash_rules_babel.exporters.native").NativeExporter
    importer = import_module("mountainash_rules_babel.importers.native").NativeImporter
    return exporter(), importer()


def _flat_lattice() -> Lattice:
    return Lattice(
        dataframe=pl.DataFrame({"region": []}, schema={"region": pl.String}),
        metadata=DimensionsMetadata(dimensions=[Dimension(dimension_name="region")]),
        aggregates=[],
        partition_key=None,
    )


def _candidate_cells(result):
    return sorted(result.candidate_cells.to_dicts(), key=lambda row: row["cell_id"])


def _candidate_contributors(result):
    return sorted(
        result.candidate_contributors.to_dicts(),
        key=lambda row: (row["cell_id"], row["source_id"]),
    )


def _lineage(result):
    return sorted(
        result.lineage.to_dicts(),
        key=lambda row: (row["output_name"], row["source_id"]),
    )


def test_native_snapshot_requires_explicit_format_selection(tmp_path):
    _, lattice, _, explicit_limits = build_exact_lattice()
    snapshot = babel.export_lattice(
        lattice, "native", path=tmp_path / "snapshot", limits=explicit_limits
    )

    with pytest.raises(babel.FormatNotFoundError):
        babel.import_lattice(snapshot, limits=explicit_limits)


def test_native_dispatch_preserves_exact_artifact_outcome_and_lineage(tmp_path):
    engine, lattice, _, explicit_limits = build_exact_lattice()
    before = engine.apply(lattice, {"x": 5}, contract_id="consumer", profile_id="quote")

    snapshot = babel.export_lattice(
        lattice, "native", path=tmp_path / "snapshot", limits=explicit_limits
    )
    restored = babel.import_lattice(snapshot, format="native", limits=explicit_limits)
    after = engine.apply(restored, {"x": 5}, contract_id="consumer", profile_id="quote")

    assert restored.artifact_kind == "exact_cells"
    assert restored.artifact_id == lattice.artifact_id
    assert restored.bindings == lattice.bindings
    assert after.outcome == before.outcome
    assert after.values["amount.sum"] == -999999999
    assert _candidate_cells(after) == _candidate_cells(before)
    assert _candidate_contributors(after) == _candidate_contributors(before)
    assert _lineage(after) == _lineage(before)


def test_native_rejects_missing_limits_bytes_and_flat_artifacts(tmp_path):
    exporter, importer = _plugins()
    flat = _flat_lattice()

    with pytest.raises(ValueError):
        exporter.export(flat, tmp_path / "flat", limits=None)
    with pytest.raises(ExportError):
        exporter.export_bytes(flat, limits=limits())
    with pytest.raises(SchemaContractError):
        exporter.export(flat, tmp_path / "flat", limits=limits())

    legacy = flat.save(tmp_path / "legacy", limits=limits())
    with pytest.raises(SchemaContractError):
        importer.import_lattice(legacy, limits=limits())


def test_native_dispatch_rejects_missing_limits_bytes_legacy_and_flat_projection(
    tmp_path,
):
    _, lattice, _, explicit_limits = build_exact_lattice()
    flat = _flat_lattice()

    with pytest.raises(ValueError):
        babel.export_lattice(lattice, "native", path=tmp_path / "missing-limits")
    with pytest.raises(ExportError):
        babel.export_lattice(lattice, "native")
    with pytest.raises(SchemaContractError):
        babel.export_lattice(
            flat, "native", path=tmp_path / "flat", limits=explicit_limits
        )
    with pytest.raises(SchemaContractError):
        babel.export_lattice(lattice, "csv")

    legacy = flat.save(tmp_path / "legacy", limits=explicit_limits)
    with pytest.raises(SchemaContractError):
        babel.import_lattice(legacy, format="native", limits=explicit_limits)


def test_native_transport_retains_candidate_alternatives_and_requested_projection(
    tmp_path,
):
    engine, lattice, rows, explicit_limits = build_exact_lattice()
    snapshot = babel.export_lattice(
        lattice, "native", path=tmp_path / "snapshot", limits=explicit_limits
    )
    restored = babel.import_lattice(snapshot, format="native", limits=explicit_limits)

    before = engine.apply(
        lattice,
        {"x": 5},
        contract_id="consumer",
        profile_id="sum-only",
        dont_care=["x"],
    )
    after = engine.apply(
        restored,
        {"x": 5},
        contract_id="consumer",
        profile_id="sum-only",
        dont_care=["x"],
    )

    assert after.outcome == before.outcome
    assert _candidate_cells(after) == _candidate_cells(before)
    assert _candidate_contributors(after) == _candidate_contributors(before)
    assert len(_candidate_cells(after)) == 2
    assert all(
        set(row) == {"cell_id", "predicate_id", "contributor_set_id", "amount.sum"}
        for row in after.candidate_cells.to_dicts()
    )
    assert {row["source_id"] for row in after.candidate_contributors.to_dicts()} == {
        row["id"] for row in rows
    }


def test_native_transport_preserves_empty_and_unanalyzed_candidate_distinctions(
    tmp_path,
):
    engine, lattice, _, explicit_limits = build_exact_lattice()
    snapshot = babel.export_lattice(
        lattice, "native", path=tmp_path / "snapshot", limits=explicit_limits
    )
    restored = babel.import_lattice(snapshot, format="native", limits=explicit_limits)

    before_empty = engine.apply(
        lattice, {"x": 15}, contract_id="consumer", profile_id="quote"
    )
    after_empty = engine.apply(
        restored, {"x": 15}, contract_id="consumer", profile_id="quote"
    )

    assert after_empty.outcome == before_empty.outcome
    assert _candidate_cells(before_empty) == []
    assert _candidate_cells(after_empty) == []

    with pytest.raises(InvalidContextError) as before_invalid:
        engine.apply(lattice, {"x": 40}, contract_id="consumer", profile_id="quote")
    with pytest.raises(InvalidContextError) as after_invalid:
        engine.apply(restored, {"x": 40}, contract_id="consumer", profile_id="quote")

    assert after_invalid.value.result.outcome == before_invalid.value.result.outcome
    assert before_invalid.value.result.candidate_cells is None
    assert after_invalid.value.result.candidate_cells is None

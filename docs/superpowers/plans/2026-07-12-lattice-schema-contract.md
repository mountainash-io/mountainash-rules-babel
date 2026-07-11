# Lattice Schema Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define and enforce the flat-vs-composed lattice contract across babel's exporters/importers, per `docs/superpowers/specs/2026-07-12-lattice-schema-contract-design.md`.

**Architecture:** Two small engine-side enablers land in mountainash-rules first (`Lattice.is_composed`, empty-build composed schema). Babel then gains `SchemaContractError`, a `LatticeManifest` sidecar model, and a single `resolve_lattice() -> LatticeView` normaliser that both exporters and the round-trip validator consume.

**Tech Stack:** Python 3.12, polars, lxml (DMN), pydantic + pyyaml (manifest), pytest via hatch in both repos.

## Global Constraints

- **Depends on** the mountainash-rules serialisable-metadata plan (YAML methods, `DataType`) and hit-policies plan (`HitPolicy` on `DimensionsMetadata`). Execute after both.
- Shape marker is `__prime_product` presence — never `co_` prefix heuristics.
- Tracking namespace: `__prime`, `__prime_product`, `__level`, `__agg_*`.
- On composed lattices the ONLY meaningful per-row values are `co_*`, tracking, and `__agg_*`; everything else is a stale anchor-rule copy.
- Sidecar is always `<name>.manifest.yaml` (`LatticeManifest`); the engine repo owns bare `DimensionsMetadata` YAML, babel owns the manifest wrapping it.
- Fail-closed: unproven claims (UNIQUE on composed, mixed shapes, colliding renames) raise `SchemaContractError`.
- Babel test commands: `hatch run test:test-quick`, `hatch run test:test-target <node>` (run from the babel repo root).
- Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Engine enablers — `Lattice.is_composed` + empty-build schema (mountainash-rules repo)

**Files (in `../mountainash-rules`):**
- Modify: `src/mountainash_rules/lattice.py`, `src/mountainash_rules/accumulator_engine.py` (`build` empty path)
- Test: `tests/test_lattice.py`

**Interfaces:**
- Produces: `Lattice.is_composed -> bool` (True iff `__prime_product` in columns); `build()` with zero matching rules returns a lattice whose (empty) frame has the full composed schema. All babel tasks consume `is_composed`.

- [ ] **Step 1: Write the failing tests** (append to `../mountainash-rules/tests/test_lattice.py`)

```python
class TestIsComposed:
    def _metadata(self):
        return DimensionsMetadata(dimensions=[
            Dimension(dimension_name="region"),
        ])

    def test_built_lattice_is_composed(self):
        engine = AccumulatorEngine(dimension_metadata=self._metadata())
        rules = pl.DataFrame({"rule_name": ["r"], "region": ["AU"]})
        assert engine.build(rules).is_composed is True

    def test_hand_constructed_flat_lattice_is_not_composed(self):
        lattice = Lattice(
            dataframe=pl.DataFrame({"rule_name": ["r"], "region": ["AU"]}),
            metadata=self._metadata(),
            aggregates=[],
            partition_key=None,
        )
        assert lattice.is_composed is False

    def test_empty_build_is_still_composed(self):
        engine = AccumulatorEngine(dimension_metadata=self._metadata())
        rules = pl.DataFrame({"rule_name": [], "region": []},
                             schema={"rule_name": pl.Utf8, "region": pl.Utf8})
        lattice = engine.build(rules)
        assert lattice.count == 0
        assert lattice.is_composed is True
        assert "co_region" in relation(lattice.combinations).columns
```

(Match import style at the top of the existing `test_lattice.py` — `AccumulatorEngine`, `Dimension`, `DimensionsMetadata`, `pl`, `relation` are likely already imported.)

- [ ] **Step 2: Run to verify failure**

Run (from `../mountainash-rules`): `hatch run test:test-target tests/test_lattice.py::TestIsComposed -v`
Expected: `is_composed` AttributeError; empty-build assertions fail (raw frame lacks `co_region`/`__prime_product`).

- [ ] **Step 3: Implement**

`lattice.py`:

```python
    @property
    def is_composed(self) -> bool:
        """True when this lattice came out of AccumulatorEngine.build().

        Keyed on the __prime_product tracking column, which only the build
        phase creates; importers strip tracking columns, so imported
        lattices are always flat.
        """
        return "__prime_product" in relation(self._df).columns
```

`accumulator_engine.py` — replace the `n_rules == 0` early return with a schema-complete empty frame:

```python
        if n_rules == 0:
            empty = rules_pl.with_columns(
                pl.Series("__prime", [], dtype=pl.Int64)
            )
            anchor = self._create_anchor(empty)
            return Lattice(
                dataframe=relation(anchor).collect(),
                metadata=self._metadata,
                aggregates=self._aggregates,
                partition_key=partition_key,
            )
```

(`_create_anchor` is pure column-adding, so it works on an empty frame; if any expression chokes on zero rows, construct the empty polars frame explicitly with the columns from `_co_fields() + _na_flag_fields() + _tracking_columns()` instead — either way the assertion set in Step 1 defines done.)

- [ ] **Step 4: Run** the new tests + `hatch run test:test-quick` (rules repo) → PASS.

- [ ] **Step 5: Commit (rules repo)**

```bash
git add src/mountainash_rules/lattice.py src/mountainash_rules/accumulator_engine.py tests/test_lattice.py
git commit -m "feat: Lattice.is_composed marker; empty builds keep composed schema

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: SchemaContractError + LatticeManifest (babel repo)

**Files:**
- Modify: `src/mountainash_rules_babel/errors.py`
- Create: `src/mountainash_rules_babel/manifest.py`
- Test: `tests/test_lattice_schema_contract.py` (create)

**Interfaces:**
- Produces: `SchemaContractError` (subclassing babel's existing base error — check `errors.py` for the base class name and match it); `LatticeManifest(BaseModel)` with `dimensions: DimensionsMetadata`, `aggregates: list[AggregateSpec]` (`column_name` + `operation`), `to_yaml/from_yaml/to_yaml_file/from_yaml_file` mirroring the engine's idiom; `LatticeManifest.for_lattice(lattice)` builder.

- [ ] **Step 1: Write the failing tests** (create `tests/test_lattice_schema_contract.py`)

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `hatch run test:test-target tests/test_lattice_schema_contract.py -v`
Expected: ImportError on `SchemaContractError` / `manifest`.

- [ ] **Step 3: Implement**

`errors.py` — append (subclass the module's existing base, e.g. `BabelError` — read the file first and use the real base name):

```python
class SchemaContractError(BabelError):
    """A lattice frame violates the flat/composed schema contract."""
```

`manifest.py`:

```python
"""LatticeManifest: the sidecar babel ships alongside exported rule tables."""

from __future__ import annotations

import pathlib

import yaml
from pydantic import BaseModel, Field

from mountainash_rules.dimension import DimensionsMetadata
from mountainash_rules.lattice import Lattice


class AggregateSpec(BaseModel):
    column_name: str
    operation: str = "sum"


class LatticeManifest(BaseModel):
    """Everything needed to rehydrate an exported table: dimensions
    (embedding the engine's DimensionsMetadata payload, hit_policy
    included) plus aggregate declarations."""

    dimensions: DimensionsMetadata
    aggregates: list[AggregateSpec] = Field(default_factory=list)

    @classmethod
    def for_lattice(cls, lattice: Lattice) -> "LatticeManifest":
        return cls(
            dimensions=lattice.metadata,
            aggregates=[
                AggregateSpec(column_name=a.column_name, operation=a.operation)
                for a in lattice.aggregates
            ],
        )

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            self.model_dump(mode="json", exclude_defaults=True),
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, text: str) -> "LatticeManifest":
        return cls.model_validate(yaml.safe_load(text))

    def to_yaml_file(self, path: "str | pathlib.Path") -> pathlib.Path:
        path = pathlib.Path(path)
        path.write_text(self.to_yaml(), encoding="utf-8")
        return path

    @classmethod
    def from_yaml_file(cls, path: "str | pathlib.Path") -> "LatticeManifest":
        return cls.from_yaml(pathlib.Path(path).read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mountainash_rules_babel/errors.py src/mountainash_rules_babel/manifest.py tests/test_lattice_schema_contract.py
git commit -m "feat: SchemaContractError and LatticeManifest sidecar model

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: resolve_lattice / LatticeView (babel repo)

**Files:**
- Modify: `src/mountainash_rules_babel/exporters/base.py`
- Test: `tests/test_lattice_schema_contract.py`

**Interfaces:**
- Produces (consumed by Tasks 4–6):

```python
@dataclass
class LatticeView:
    df: pl.DataFrame              # authoritative values under flat names
    metadata: DimensionsMetadata
    is_composed: bool
    output_columns: list[str]     # incl. renamed aggregates
    dropped_stale: list[str]      # composed only: excluded anchor copies
    tracking: pl.DataFrame | None # __prime*, __level (+ __agg originals)

TRACKING_COLUMNS = ("__prime", "__prime_product", "__level")

def resolve_lattice(lattice: Lattice, *, include_tracking: bool = False) -> LatticeView
```

- [ ] **Step 1: Write the failing tests** (append)

```python
from mountainash_rules_babel.exporters.base import resolve_lattice


class TestResolveLattice:
    def test_composed_values_are_coalesced_under_flat_names(self):
        view = resolve_lattice(_composed_lattice())
        assert view.is_composed is True
        # co_lvr_min renamed to lvr_min; pair row [70, 80] must exist
        pairs = view.df.filter(pl.col("lvr_min") == 70)
        assert pairs["lvr_max"].to_list() == [80]

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
```

Note on the first test: `_flat_lattice`'s composed sibling builds R1 `[60,80]` + R2 `[70,90]`; the frontier keeps the pair `[70,80]` and any non-dominated singletons — the assertion targets the pair row only, which is stable regardless of frontier details.

- [ ] **Step 2: Run to verify failure** — ImportError on `resolve_lattice`.

- [ ] **Step 3: Implement** (append to `exporters/base.py`)

```python
from dataclasses import dataclass, field

from mountainash_rules.constants import MatchStrategy
from mountainash_rules.dimension import DimensionsMetadata

from mountainash_rules_babel.errors import SchemaContractError

TRACKING_COLUMNS = ("__prime", "__prime_product", "__level")


@dataclass
class LatticeView:
    df: pl.DataFrame
    metadata: DimensionsMetadata
    is_composed: bool
    output_columns: list[str]
    dropped_stale: list[str] = field(default_factory=list)
    tracking: "pl.DataFrame | None" = None


def _dimension_value_columns(metadata: DimensionsMetadata) -> list[str]:
    cols: list[str] = []
    for d in metadata.dimensions:
        if d.match_strategy == MatchStrategy.RANGE:
            cols.extend([d.range_min_field, d.range_max_field])
        else:
            cols.append(d.resolved_rule_field)
    return cols


def resolve_lattice(lattice, *, include_tracking: bool = False) -> LatticeView:
    """Normalise a lattice to authoritative values under flat column names."""
    df = lattice_to_polars(lattice)
    dim_cols = _dimension_value_columns(lattice.metadata)

    if not lattice.is_composed:
        tracked = [
            c for c in df.columns
            if c in TRACKING_COLUMNS or c.startswith("__agg_")
        ]
        if tracked:
            raise SchemaContractError(
                f"Flat lattice contains tracking columns {tracked}; "
                f"mixed shapes are not exportable"
            )
        output_columns = [
            c for c in df.columns if c not in dim_cols and c != "rule_name"
        ]
        return LatticeView(
            df=df, metadata=lattice.metadata, is_composed=False,
            output_columns=output_columns,
        )

    # Composed: co_ columns are authoritative; anchor copies are stale.
    co_renames = {f"co_{c}": c for c in dim_cols}
    na_cols = [c for c in df.columns if c.startswith("co_") and c.endswith("_na")]
    agg_renames = {
        c: c.removeprefix("__agg_")
        for c in df.columns if c.startswith("__agg_")
    }
    tracking_cols = [c for c in df.columns if c in TRACKING_COLUMNS]

    keep = list(co_renames) + list(agg_renames)
    stale = [
        c for c in df.columns
        if c not in keep and c not in na_cols and c not in tracking_cols
    ]
    for src, dst in agg_renames.items():
        if dst in co_renames.values():
            raise SchemaContractError(
                f"Aggregate column {src} would rename onto dimension "
                f"column {dst}"
            )

    tracking = df.select(tracking_cols) if include_tracking else None
    out = df.select(keep).rename({**co_renames, **agg_renames})
    return LatticeView(
        df=out,
        metadata=lattice.metadata,
        is_composed=True,
        output_columns=sorted(agg_renames.values()),
        dropped_stale=sorted(stale),
        tracking=tracking,
    )
```

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mountainash_rules_babel/exporters/base.py tests/test_lattice_schema_contract.py
git commit -m "feat: resolve_lattice normaliser enforcing the schema contract

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: CsvExporter on LatticeView + manifest sidecar

**Files:**
- Modify: `src/mountainash_rules_babel/exporters/csv_.py`
- Test: `tests/test_lattice_schema_contract.py`

**Interfaces:**
- Produces: `CsvExporter.export(lattice, path, *, include_tracking=False, manifest_sidecar=True, **options)`; sentinels → empty cells; sidecar `<stem>.manifest.yaml` next to the CSV.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure** — `co_` columns present, sentinel literals in the file, no sidecar.

- [ ] **Step 3: Implement** (rewrite `csv_.py` export path)

```python
from __future__ import annotations

from pathlib import Path

import polars as pl

from mountainash_rules.constants import (
    NOT_SET,
    NOT_SET_NUMERIC,
    UNKNOWN,
    UNKNOWN_NUMERIC,
)
from mountainash_rules.lattice import Lattice

from mountainash_rules_babel.exporters.base import resolve_lattice
from mountainash_rules_babel.manifest import LatticeManifest

_STRING_SENTINELS = [UNKNOWN, NOT_SET]
_NUMERIC_SENTINELS = [UNKNOWN_NUMERIC, NOT_SET_NUMERIC]


def _sentinels_to_null(df: pl.DataFrame) -> pl.DataFrame:
    exprs = []
    for name, dtype in df.schema.items():
        if dtype == pl.Utf8:
            exprs.append(
                pl.when(pl.col(name).is_in(_STRING_SENTINELS))
                .then(None).otherwise(pl.col(name)).alias(name)
            )
        elif dtype.is_numeric():
            exprs.append(
                pl.when(pl.col(name).is_in(_NUMERIC_SENTINELS))
                .then(None).otherwise(pl.col(name)).alias(name)
            )
    return df.with_columns(exprs) if exprs else df


class CsvExporter:
    name: str = "csv"
    file_extension: str = ".csv"

    def _frame(self, lattice: Lattice, include_tracking: bool) -> pl.DataFrame:
        view = resolve_lattice(lattice, include_tracking=include_tracking)
        df = _sentinels_to_null(view.df)
        if include_tracking and view.tracking is not None:
            df = pl.concat([df, view.tracking], how="horizontal")
        return df

    def export(
        self,
        lattice: Lattice,
        path: Path,
        *,
        include_tracking: bool = False,
        manifest_sidecar: bool = True,
        **options,
    ) -> Path:
        path = Path(path)
        self._frame(lattice, include_tracking).write_csv(path)
        if manifest_sidecar:
            LatticeManifest.for_lattice(lattice).to_yaml_file(
                path.with_suffix(".manifest.yaml")
            )
        return path

    def export_bytes(self, lattice: Lattice, *, include_tracking: bool = False,
                     **options) -> bytes:
        csv_str = self._frame(lattice, include_tracking).write_csv()
        return csv_str.encode("utf-8") if isinstance(csv_str, str) else csv_str
```

(Temporal sentinels join `_sentinels_to_null` when the metadata plan's `UNKNOWN_DATE` family exists — add a `pl.Date`/`pl.Datetime` branch mirroring the numeric one.)

- [ ] **Step 4: Run** → PASS; existing csv exporter tests → update any that asserted raw-frame dumps (they asserted the old, pre-contract behaviour; cite the spec in the commit message).

- [ ] **Step 5: Commit**

```bash
git add src/mountainash_rules_babel/exporters/csv_.py tests/
git commit -m "feat: CSV export honours schema contract with manifest sidecar

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: CsvImporter — sidecar autoload, sentinel fill, tracking strip

**Files:**
- Modify: `src/mountainash_rules_babel/importers/csv_.py`
- Test: `tests/test_lattice_schema_contract.py`

**Interfaces:**
- Consumes: `LatticeManifest`, metadata-plan `metadata=` parameter (already landed).
- Produces: auto-loads `<stem>.manifest.yaml`; empty cells → typed sentinels per dimension `data_type`; strips tracking columns with a warning; always returns a flat lattice; manifest aggregates rehydrated.

- [ ] **Step 1: Write the failing tests**

```python
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
        df = lattice.combinations
        # R2's region was <NA> -> exported empty -> re-imported as UNKNOWN
        assert UNKNOWN in df["region"].to_list()
        assert UNKNOWN_NUMERIC not in df["lvr_min"].to_list() or \
            df["lvr_min"].null_count() == 0

    def test_tracking_columns_stripped_with_warning(self, tmp_path):
        p = self._export(tmp_path, include_tracking=True)
        with pytest.warns(UserWarning, match="__prime_product"):
            lattice = CsvImporter().import_lattice(p)
        assert lattice.is_composed is False

    def test_import_is_always_flat(self, tmp_path):
        p = self._export(tmp_path)
        assert CsvImporter().import_lattice(p).is_composed is False
```

(For `test_empty_cells_become_typed_sentinels`: the export nulls sentinel values; the import must fill nulls in dimension columns back to the type's UNKNOWN sentinel so the round-trip is lossless. Assert the exact frame in Task 7's round-trip; here assert the region sentinel and zero remaining nulls in dimension columns.)

- [ ] **Step 2: Run to verify failure** — no sidecar autoload; nulls stay null; tracking columns pass through making `is_composed` True.

- [ ] **Step 3: Implement** (extend `import_lattice` — after the metadata-plan version of the method)

```python
import warnings

from mountainash_rules.constants import (
    UNKNOWN,
    UNKNOWN_NUMERIC,
    MatchStrategy,
)
from mountainash_rules_babel.exporters.base import TRACKING_COLUMNS
from mountainash_rules_babel.manifest import LatticeManifest


    def import_lattice(self, path, *, metadata=None, dimension_columns=None,
                       aggregate_columns=None, **options) -> Lattice:
        path = Path(path)
        df = pl.read_csv(path)

        # Strip tracking columns: imports never carry composed state.
        tracked = [
            c for c in df.columns
            if c in TRACKING_COLUMNS or c.startswith("__agg_")
        ]
        if tracked:
            warnings.warn(
                f"Stripping tracking columns on import: {tracked} "
                f"(diagnostic output only; recombination is "
                f"AccumulatorEngine.build()'s job)",
                UserWarning,
            )
            df = df.drop(tracked)

        manifest: LatticeManifest | None = None
        sidecar = path.with_suffix(".manifest.yaml")
        if metadata is None and sidecar.exists():
            manifest = LatticeManifest.from_yaml_file(sidecar)
            metadata = manifest.dimensions

        if metadata is not None:
            if isinstance(metadata, (str, Path)):
                loaded = yaml.safe_load(Path(metadata).read_text())
                if "dimensions" in loaded and isinstance(loaded["dimensions"], dict):
                    manifest = LatticeManifest.from_yaml_file(metadata)
                    metadata = manifest.dimensions
                else:
                    metadata = DimensionsMetadata.from_yaml_file(metadata)
            df = self._fill_sentinels(df, metadata)
            aggregates = (
                [Aggregate(column_name=a.column_name, operation=a.operation)
                 for a in manifest.aggregates]
                if manifest is not None
                else [Aggregate(column_name=c, operation=op)
                      for c, op in (aggregate_columns or {}).items()]
            )
            self._validate_columns(df, metadata)
            return Lattice(dataframe=df, metadata=metadata,
                           aggregates=aggregates, partition_key=None)

        # inference fallback unchanged
        ...

    @staticmethod
    def _fill_sentinels(df: pl.DataFrame, metadata: DimensionsMetadata) -> pl.DataFrame:
        exprs = []
        for dim in metadata.dimensions:
            if dim.match_strategy == MatchStrategy.RANGE:
                cols, sentinel = (
                    [dim.range_min_field, dim.range_max_field], UNKNOWN_NUMERIC,
                )
            else:
                cols = [dim.resolved_rule_field]
                sentinel = (
                    UNKNOWN_NUMERIC
                    if getattr(dim.data_type, "is_numeric", False)
                    else UNKNOWN
                )
            for c in cols:
                if c in df.columns:
                    exprs.append(pl.col(c).fill_null(sentinel))
        return df.with_columns(exprs) if exprs else df
```

(`_validate_columns` is the missing-column check from the metadata plan — factor it out of the earlier inline block. The `loaded["dimensions"]` sniff distinguishes a manifest from bare `DimensionsMetadata` YAML, whose top level is also `dimensions:` but holding a **list**; hence the `isinstance(..., dict)` — verify against a real file at RED time and adjust: a manifest's `dimensions` key holds the DimensionsMetadata *mapping* (which itself contains a `dimensions` list), a bare metadata file's `dimensions` key holds a list.)

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mountainash_rules_babel/importers/csv_.py tests/test_lattice_schema_contract.py
git commit -m "feat: CSV import - manifest autoload, sentinel fill, tracking strip

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: DmnExporter on LatticeView + hitPolicy

**Files:**
- Modify: `src/mountainash_rules_babel/exporters/dmn.py`
- Test: `tests/test_lattice_schema_contract.py`

**Interfaces:**
- Consumes: `resolve_lattice`, `HitPolicy` on metadata, `SchemaContractError`.
- Produces: DMN input entries read resolved flat names (coalesced values on composed lattices); `hitPolicy` from `metadata.hit_policy` (`rule_order → "RULE ORDER"`, others uppercased); `is_composed and UNIQUE` → `SchemaContractError` unless `assume_unique=True`; rule ids are row indices; `include_tracking=True` adds `__prime_product` as rule `description`.

- [ ] **Step 1: Write the failing tests**

```python
from lxml import etree

from mountainash_rules_babel.exporters.dmn import DmnExporter


def _dmn_tree(lattice, **options):
    data = DmnExporter().export_bytes(lattice, **options)
    return etree.fromstring(data)


NS = {"dmn": "https://www.omg.org/spec/DMN/20191111/MODEL/"}


class TestDmnContract:
    def test_composed_inputs_are_coalesced(self):
        tree = _dmn_tree(_composed_lattice())
        entries = [
            e.text for e in tree.findall(".//dmn:inputEntry/dmn:text", NS)
        ]
        assert "[70..80]" in entries  # the coalesced pair, not a seed rule

    def test_no_internal_columns_in_outputs(self):
        tree = _dmn_tree(_composed_lattice())
        labels = [o.get("label") for o in tree.findall(".//dmn:output", NS)]
        assert labels == ["margin"]

    def test_hit_policy_from_metadata_default_collect(self):
        tree = _dmn_tree(_composed_lattice())
        dt = tree.find(".//dmn:decisionTable", NS)
        assert dt.get("hitPolicy") == "COLLECT"

    def test_unique_on_composed_fails_closed(self):
        lattice = _composed_lattice()
        lattice.metadata.hit_policy = HitPolicy.UNIQUE
        with pytest.raises(SchemaContractError, match="unique"):
            DmnExporter().export_bytes(lattice)
        # assume_unique overrides
        data = DmnExporter().export_bytes(lattice, assume_unique=True)
        assert b'hitPolicy="UNIQUE"' in data
```

(Import `HitPolicy` from `mountainash_rules.constants`. If `DimensionsMetadata` is frozen/validate-on-assign, build the UNIQUE metadata up front via `_metadata().model_copy(update={"hit_policy": HitPolicy.UNIQUE})` and construct the lattice with it instead of mutating — check pydantic config at RED time.)

- [ ] **Step 2: Run to verify failure** — inputs carry seed values, hitPolicy hardcoded UNIQUE, no guard.

- [ ] **Step 3: Implement** (rework `DmnExporter.export_bytes`)

```python
from mountainash_rules.constants import DataType, HitPolicy, MatchStrategy

from mountainash_rules_babel.errors import SchemaContractError
from mountainash_rules_babel.exporters.base import resolve_lattice

_DMN_POLICY = {
    HitPolicy.COLLECT: "COLLECT",
    HitPolicy.UNIQUE: "UNIQUE",
    HitPolicy.FIRST: "FIRST",
    HitPolicy.PRIORITY: "PRIORITY",
    HitPolicy.ANY: "ANY",
    HitPolicy.RULE_ORDER: "RULE ORDER",
}


    def export_bytes(self, lattice: Lattice, *, include_tracking: bool = False,
                     assume_unique: bool = False, **options) -> bytes:
        decision_name = options.get("decision_name", "GeneratedDecision")
        table_name = options.get("table_name", "GeneratedTable")

        view = resolve_lattice(lattice, include_tracking=include_tracking)
        policy = lattice.metadata.hit_policy
        if view.is_composed and policy == HitPolicy.UNIQUE and not assume_unique:
            raise SchemaContractError(
                "hit_policy=unique is unproven for a composed lattice "
                "(distinct maximal combinations can overlap); run a "
                "conflicts analysis and pass assume_unique=True to override"
            )

        # ... XML skeleton as before, but:
        dt.set("hitPolicy", _DMN_POLICY[policy])

        rows = view.df.to_dicts()
        tracking_rows = (
            view.tracking.to_dicts() if view.tracking is not None else None
        )
        for row_idx, row in enumerate(rows):
            rule_el = etree.SubElement(dt, f"{{{DMN_NS}}}rule")
            rule_el.set("id", f"rule_{row_idx}")
            if tracking_rows is not None:
                desc = etree.SubElement(rule_el, f"{{{DMN_NS}}}description")
                desc.text = (
                    f"prime_product={tracking_rows[row_idx]['__prime_product']}"
                )
            # input entries: unchanged logic, but row comes from view.df,
            # so dim.range_min_field / dim.dimension_name hit the resolved
            # flat-name columns
            ...
        # output entries iterate view.output_columns
```

Keep `_feel_entry`/`_feel_range_entry` as-is (they already sentinel-check; after the CSV task the view still carries in-band sentinels — resolve_lattice does not null them, only the CSV writer does). Delete the old `range_extra_cols`/`output_cols` computation.

- [ ] **Step 4: Run** → new tests PASS; existing DMN tests updated where they asserted `hitPolicy="UNIQUE"` (now COLLECT by default — the old assertion was the defect).

- [ ] **Step 5: Commit**

```bash
git add src/mountainash_rules_babel/exporters/dmn.py tests/
git commit -m "feat: DMN export uses resolved lattice view and metadata hit policy

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Round-trip validator + contract doc

**Files:**
- Modify: `src/mountainash_rules_babel/validators/round_trip.py`
- Create: `docs/lattice-schema.md`
- Test: `tests/test_lattice_schema_contract.py`

**Interfaces:**
- Consumes: everything above.
- Produces: CSV round-trip validation is real (export → import → frame + manifest equality, modulo CSV int/float widening); DMN stays fail-closed; the contract doc records the column taxonomy table from the spec.

- [ ] **Step 1: Write the failing tests**

```python
class TestRoundTrip:
    def test_full_csv_round_trip(self, tmp_path):
        original = _composed_lattice()
        view = resolve_lattice(original)
        p = CsvExporter().export(original, tmp_path / "rt.csv")
        imported = CsvImporter().import_lattice(p)

        imported_df = imported.combinations.select(sorted(view.df.columns))
        expected_df = view.df.select(sorted(view.df.columns))
        # CSV widens ints; cast expected to the imported schema first
        expected_df = expected_df.cast(imported_df.schema)
        assert imported_df.sort(imported_df.columns).equals(
            expected_df.sort(expected_df.columns)
        )
        assert imported.metadata == original.metadata

    def test_round_trip_validator_passes_csv(self, tmp_path):
        from mountainash_rules_babel.validators.round_trip import (
            RoundTripValidator,
        )
        result = RoundTripValidator().validate(
            _composed_lattice(), format="csv", workdir=tmp_path
        )
        assert result.passed

    def test_round_trip_validator_fails_closed_on_dmn(self, tmp_path):
        from mountainash_rules_babel.validators.round_trip import (
            RoundTripValidator,
        )
        result = RoundTripValidator().validate(
            _composed_lattice(), format="dmn", workdir=tmp_path
        )
        assert not result.passed
```

(Match `RoundTripValidator.validate`'s real signature and result type — read `validators/base.py` and the current stub first; if the validator returns issues/warnings rather than a `.passed` object, assert in that idiom instead. The stub's fail-closed behaviour for DMN must be preserved as an explicit not-supported failure, not a pass.)

- [ ] **Step 2: Run to verify failure** — validator is a warning stub.

- [ ] **Step 3: Implement** the CSV branch of `RoundTripValidator.validate`: export via `CsvExporter` to `workdir`, re-import via `CsvImporter`, compare exactly as the Step 1 test does (share the comparison as a module-level `frames_equivalent(a, b) -> list[str]` returning human-readable differences), and report metadata inequality as a failure with the differing fields named. DMN branch: return the existing explicit not-supported failure.

- [ ] **Step 4: Write `docs/lattice-schema.md`** — transcribe the spec's §1 column-taxonomy table verbatim, add the don't-care encoding rule (in-band sentinels inside frames; empty cells at the CSV boundary), the "imports are always flat / recombination is build()'s job" rule, and links to `mountainash-central/01.principles/mountainash-rules/` and the two upstream specs. This is documentation of decisions already made — no new decisions in this file.

- [ ] **Step 5: Run the full babel suite**

Run: `hatch run test:test-quick` → PASS.

- [ ] **Step 6: Commit and push**

```bash
git add src/mountainash_rules_babel/validators/round_trip.py docs/lattice-schema.md tests/
git commit -m "feat: real CSV round-trip validation and lattice schema contract doc

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin develop
```

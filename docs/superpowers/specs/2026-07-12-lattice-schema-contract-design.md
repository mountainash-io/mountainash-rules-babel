# Lattice Schema Contract: Flat vs Composed, Column Resolution, Export Semantics

> **Status:** APPROVED FOR PLANNING
> **Date:** 2026-07-12
> **Source:** Architectural review 2026-07-12 §1.6; backlog card
> `mountainash-central/01.principles/mountainash-rules-babel/h.backlog/lattice-schema-contract.md`
> **Depends on (mountainash-rules specs, same date):**
> serialisable-dimension-metadata (YAML sidecar, `DataType`),
> hit-policies (`HitPolicy` on `DimensionsMetadata`).
> **Principles:** fail-closed validators; babel never guesses silently.

## Problem

Babel's exporters assume a **flat** lattice — original rule columns named by
`dimension_name`/`range_*_field`. But `AccumulatorEngine.build()` produces a
**composed** lattice whose values live in `co_`-prefixed columns, plus
tracking columns (`__prime`, `__prime_product`, `__level`), NA flags
(`co_*_na`), and aggregate columns (`__agg_*`). Consequences today:

- `DmnExporter` reads `row.get(dim.dimension_name)` / `row.get(dim.range_min_field)`
  — on a composed lattice these are the *original single-rule* columns carried
  through the build, i.e. **wrong values** (the last-joined rule's, not the
  coalesced combination's), while `co_*` columns leak into `output_cols`.
- `CsvExporter` dumps everything, tracking columns included, with no contract
  for what a re-import means.
- `DmnExporter` hardcodes `hitPolicy="UNIQUE"`, which is false for composed
  lattices (their rows overlap by construction).

There is no written definition of the two shapes anywhere. This spec is that
definition plus the exporter/importer changes that honour it.

## Design

### 1. The contract (new doc: `docs/lattice-schema.md`, babel repo)

A glossary-style reference defining, for both shapes, exactly which columns
exist and who owns them:

| Column class | Pattern | Flat | Composed | Export? |
|---|---|---|---|---|
| Dimension values | `dimension_name` / `rule_field` / `range_*_field` | ✓ (authoritative) | present but **stale** — never read | flat only |
| Coalesced values | `co_<rule_field>`, `co_<range_*_field>` | ✗ | ✓ (authoritative) | composed only, emitted **under the flat names** |
| NA flags | `co_<field>_na`, `co_<dim>_na` | ✗ | ✓ | never (encoded as empty/don't-care cells) |
| Tracking | `__prime`, `__prime_product`, `__level` | ✗ | ✓ | opt-in (`include_tracking=True`) |
| Aggregates | `__agg_<name>` | ✗ | ✓ | ✓, renamed to `<name>` |
| Outputs | everything else except `rule_name` | ✓ | ✓ | ✓ |
| Identity | `rule_name` | ✓ | ✓ | ✓ (composed: provenance list may replace it, see §4) |

The doc also states the don't-care encoding (sentinels ↔ empty cells at the
format boundary) and cross-links the mountainash-rules principle docs. It is
the contract both repos test against.

### 2. `Lattice.is_composed` (mountainash-rules, one-line addition)

```python
@property
def is_composed(self) -> bool:
    return "__prime_product" in relation(self._df).columns
```

`__prime_product` is present iff the frame came out of `build()` (the anchor
adds it at level 0); importers never create it. Babel keys all shape
decisions off this property — no heuristics over column name patterns.

### 3. Shared column resolution (`exporters/base.py`)

One helper used by every exporter (and the round-trip validator), replacing
per-exporter guesswork:

```python
@dataclass
class LatticeView:
    df: pl.DataFrame            # normalised: authoritative values under flat names
    metadata: DimensionsMetadata
    is_composed: bool
    output_columns: list[str]   # incl. renamed aggregates
    tracking: pl.DataFrame | None  # __prime*, __level (+ rule provenance), if composed

def resolve_lattice(lattice: Lattice, *, include_tracking: bool = False) -> LatticeView
```

`resolve_lattice`:

1. Materialises via the existing `lattice_to_polars`.
2. If composed: drops the stale original dimension columns, renames each
   `co_<field>` → `<field>`, drops `co_*_na` flags (the sentinel values in
   the renamed columns already carry don't-care; flags are redundant at the
   boundary), renames `__agg_<name>` → `<name>` (collision with an existing
   column → `SchemaContractError`, fail-closed), and splits tracking columns
   out into `.tracking`.
3. If flat: passes columns through; asserts no `co_`/`__`-prefixed columns
   are present (mixed shape → `SchemaContractError`).
4. Computes `output_columns` = df columns − dimension value columns −
   `rule_name`.

`SchemaContractError` is a new babel error type (extends the existing error
hierarchy in `errors.py`).

Both `CsvExporter` and `DmnExporter` rewrite their column handling on top of
`LatticeView`; `DmnExporter`'s local `range_extra_cols`/`output_cols` logic
is deleted.

### 4. Exporter semantics changes

- **CSV**: exports `LatticeView.df` (authoritative values, flat names,
  aggregates renamed). `include_tracking=True` appends the tracking columns
  verbatim (documented as non-portable, for diagnostics). Sentinel values are
  written as empty cells (`null`), matching the import direction. A metadata
  sidecar `<name>.metadata.yaml` (from the serialisation spec's
  `to_yaml_file`) is written alongside unless `metadata_sidecar=False`.
- **DMN**: input entries read the resolved flat-name columns — composed
  lattices now export the *coalesced* intervals/values (the actual defect
  fix). Output entries come from `output_columns`. `hitPolicy` is taken from
  `lattice.metadata.hit_policy` (hit-policies spec) with the mapping defined
  there; the composed-shape guard: if `is_composed` and the policy is UNIQUE,
  raise `SchemaContractError` unless the caller passes
  `assume_unique=True` — composed rows overlap by construction, so UNIQUE is
  only claimable after an external conflicts check. Default metadata policy
  COLLECT therefore exports cleanly with no option.
- Combination provenance (`__prime_product`) is exported in DMN only as a
  rule-level `description` annotation when `include_tracking=True`
  (informational; DMN has no semantic slot for it).

### 5. Importer round-trip

`CsvImporter` (already gaining `metadata=` in the serialisation spec):

- Reads empty cells → typed sentinels per the metadata's `DataType`
  (string → `UNKNOWN`, numeric → `UNKNOWN_NUMERIC`, temporal →
  `UNKNOWN_DATE`/`UNKNOWN_DATETIME`).
- With a metadata sidecar present next to the CSV
  (`<name>.metadata.yaml`), it is loaded automatically unless `metadata=` is
  passed explicitly.
- Always produces a **flat** lattice — a re-imported composed export is a
  plain rule table whose rows happen to be combinations. Recombining is
  `AccumulatorEngine.build()`'s job, never the importer's (build/apply
  separation). The contract doc states this explicitly.
- Aggregate columns: when the sidecar carries aggregate declarations
  (`Lattice.aggregates` serialised into the sidecar alongside dimensions —
  a small `LatticeManifest` wrapper model: `dimensions` + `aggregates` +
  `hit_policy` travel together), they are rehydrated without the current
  `aggregate_columns=` manual mapping. The manifest model lives in babel
  (it is a format concern, not an engine concern) and wraps the engine's
  `DimensionsMetadata` YAML rather than forking it.

### 6. Round-trip validator

`validators/round_trip.py` (currently a fail-closed stub) becomes real for
CSV: export composed lattice → import with sidecar → assert the imported
flat frame equals `LatticeView.df` (column set, dtypes modulo CSV's
int/float widening, values with sentinel normalisation) and the imported
metadata equals the original. DMN round-trip remains fail-closed (importer
for DMN doesn't exist yet) — the validator raises its existing explicit
not-supported error rather than passing vacuously.

### Approaches considered

- **Make `build()` output flat names directly (no `co_` prefix)** —
  rejected: the build phase needs both the running coalesced value and the
  RHS rule's raw column in the same joined frame; renaming at the end would
  ease babel but destroy the lattice's provenance-bearing shape and break
  `_build_apply_metadata`. The boundary translation belongs in babel.
- **Per-exporter resolution logic** (status quo, patched) — rejected: two
  copies already diverged once; the round-trip validator needs the same
  resolution a third time.
- **Heuristic shape detection from `co_` prefixes** — rejected in favour of
  the `__prime_product` marker + `is_composed`: `co_` could legitimately
  appear in user rule columns; the tracking column cannot.

## Testing (TDD)

`tests/test_lattice_schema_contract.py` (babel, new), RED first:

1. `resolve_lattice` on a composed lattice (built by a real
   `AccumulatorEngine.build()` over RANGE + EXACT dims with one aggregate):
   flat names carry coalesced values, stale originals dropped, `__agg_x` →
   `x`, tracking split out; on a flat lattice: passthrough; on a mixed frame:
   `SchemaContractError`.
2. `Lattice.is_composed` true for built, false for imported (test lives in
   mountainash-rules' suite for the property itself; babel tests consume it).
3. DMN export of a composed lattice: input entries contain the coalesced
   interval `[10..20]`, not the last-joined rule's; no `co_*`/`__*` labels
   anywhere in the XML; `hitPolicy` reflects metadata; UNIQUE + composed →
   error without `assume_unique`.
4. CSV export: no tracking columns by default; `include_tracking=True` adds
   them; sentinels serialised as empty cells; sidecar written and parseable.
5. Full CSV round-trip: build → export → import (sidecar auto-load) →
   frames and manifest equal; aggregates rehydrated without
   `aggregate_columns=`.
6. Round-trip validator passes on CSV, still fails closed on DMN.

## Files touched

- babel: `exporters/base.py` (`LatticeView`, `resolve_lattice`),
  `exporters/csv_.py`, `exporters/dmn.py`, `importers/csv_.py`,
  `errors.py` (`SchemaContractError`), `validators/round_trip.py`,
  new `docs/lattice-schema.md`, new manifest model module
  (`mountainash_rules_babel/manifest.py`).
- mountainash-rules: `lattice.py` (`is_composed`) + its unit test.

## Out of scope

- DMN importer (separate backlog item; round-trip stays fail-closed).
- Decomposing an imported combination table back into atomic rules
  (decomposers backlog).
- Exporting multiple partitions/lattices into one document (DRG territory,
  P2).

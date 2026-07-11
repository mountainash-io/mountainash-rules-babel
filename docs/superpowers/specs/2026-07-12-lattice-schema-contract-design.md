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
  through the build, i.e. **wrong values** (the anchor/seed rule's, carried
  forward unchanged through every expansion — `_expand_level` keeps LHS
  columns and discards the `_rhs` side — not the coalesced combination's),
  while `co_*` columns leak into `output_cols`.
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
| Dimension values | `dimension_name` / `rule_field` / `range_*_field` | ✓ (authoritative) | present but **stale** (anchor rule's values, carried unchanged) — never read | flat only |
| Coalesced values | `co_<rule_field>`, `co_<range_*_field>` | ✗ | ✓ (authoritative) | composed only, emitted **under the flat names** |
| NA flags | `co_<field>_na`, `co_<dim>_na` | ✗ | ✓ | never (encoded as empty/don't-care cells) |
| Tracking | `__prime`, `__prime_product`, `__level` | ✗ | ✓ | opt-in (`include_tracking=True`) |
| Aggregates | `__agg_<name>` | ✗ | ✓ | ✓, renamed to `<name>` |
| Non-dimension passthrough | everything else except `rule_name` | ✓ (outputs, authoritative) | present but **stale** (anchor rule's values, not recomputed) | flat only |
| Identity | `rule_name` | ✓ | ✓ (anchor rule's) | ✓ flat; composed: replaced by provenance (see §4) |

The composed-shape rows carry the **anchor (seed) rule's** original columns
forward unchanged — `_expand_level` selects `current_level.columns` after
each join, discarding the `_rhs` side. So on a composed lattice the *only*
meaningful per-row values are the `co_*` columns, the tracking columns, and
the `__agg_*` accumulations. Everything else — including non-dimension
"output" columns and `rule_name` — is a stale copy from one member rule and
must not be exported as if it described the combination.

The doc also states the don't-care encoding (sentinels ↔ empty cells at the
format boundary) and cross-links the mountainash-rules principle docs. It is
the contract both repos test against.

### 2. `Lattice.is_composed` (mountainash-rules)

```python
@property
def is_composed(self) -> bool:
    return "__prime_product" in relation(self._df).columns
```

Two supporting changes in mountainash-rules make the marker reliable:

1. **Empty-build schema fix**: `build()` currently returns the raw filtered
   rules frame when `n_rules == 0`, which lacks all composed columns — an
   empty built lattice would read as flat. `build()` changes to construct
   the empty frame with the full composed schema (co_ columns, NA flags,
   tracking columns), so `is_composed` holds for every `build()` output.
2. **Import never re-composes**: babel's importers strip `__`-prefixed
   tracking columns (with a warning listing them) before constructing the
   `Lattice`, so a CSV exported with `include_tracking=True` re-imports as
   flat — tracking columns are diagnostic output, never re-imported state.
   This keeps "imports always produce a flat lattice" true by construction
   rather than by convention.

Babel keys all shape decisions off this property — no heuristics over
column name patterns.

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
2. If composed: drops **all** stale anchor-carried columns — original
   dimension columns *and* non-dimension passthrough columns *and*
   `rule_name` (their names are recorded in `LatticeView.dropped_stale` so
   callers can see what was excluded); renames each `co_<field>` →
   `<field>`; drops `co_*_na` flags (for the accumulator-supported
   strategies, the sentinel values in the renamed columns carry don't-care
   equivalently — this claim is scoped to EXACT/RANGE/GT/LT, the only
   composable strategies today); renames `__agg_<name>` → `<name>`
   (collision with a remaining column → `SchemaContractError`,
   fail-closed); splits tracking columns out into `.tracking`.
3. If flat: passes columns through; asserts no **tracking** columns
   (`__prime`, `__prime_product`, `__level`, `__agg_*`) are present (mixed
   shape → `SchemaContractError`). `co_`-prefixed user columns are legal in
   flat lattices — the assertion is deliberately restricted to the tracking
   namespace, which is the reliable marker.
4. Computes `output_columns`: flat → df columns − dimension value columns −
   `rule_name`; composed → the renamed aggregate columns only (everything
   else meaningful is a dimension value).

`SchemaContractError` is a new babel error type (extends the existing error
hierarchy in `errors.py`).

Both `CsvExporter` and `DmnExporter` rewrite their column handling on top of
`LatticeView`; `DmnExporter`'s local `range_extra_cols`/`output_cols` logic
is deleted.

### 4. Exporter semantics changes

- **CSV**: exports `LatticeView.df` (authoritative values, flat names,
  aggregates renamed). `include_tracking=True` appends the tracking columns
  verbatim (documented as non-portable diagnostics; stripped with a warning
  on re-import, per §2). Sentinel values are written as empty cells
  (`null`), matching the import direction. A manifest sidecar
  `<name>.manifest.yaml` (see §5) is written alongside unless
  `manifest_sidecar=False`.
- **DMN**: input entries read the resolved flat-name columns — composed
  lattices now export the *coalesced* intervals/values (the actual defect
  fix). Output entries come from `output_columns`. `hitPolicy` is taken from
  `lattice.metadata.hit_policy` (hit-policies spec) with the mapping defined
  there; the composed-shape guard: if `is_composed` and the policy is UNIQUE,
  raise `SchemaContractError` unless the caller passes `assume_unique=True`.
  Rationale: the build makes no uniqueness guarantee — the frontier filter
  removes dominated duplicates within a fingerprint, but distinct maximal
  combinations routinely overlap on the same context — so UNIQUE is unproven
  without a conflicts analysis, and babel fails closed on unproven claims.
  Default metadata policy COLLECT therefore exports cleanly with no option.
- Composed rows have no meaningful `rule_name` (it is the anchor rule's);
  DMN rule `id`s use the row index, and provenance carries identity when
  requested (below).
- Combination provenance (`__prime_product`) is exported in DMN only as a
  rule-level `description` annotation when `include_tracking=True`
  (informational; DMN has no semantic slot for it).

### 5. Importer round-trip

`CsvImporter` (already gaining `metadata=` in the serialisation spec):

- Reads empty cells → typed sentinels per the metadata's `DataType`
  (string → `UNKNOWN`, numeric → `UNKNOWN_NUMERIC`, temporal →
  `UNKNOWN_DATE`/`UNKNOWN_DATETIME`).
- With a manifest sidecar present next to the CSV
  (`<name>.manifest.yaml`), it is loaded automatically unless `metadata=` is
  passed explicitly.
- Tracking columns (`__prime`, `__prime_product`, `__level`, `__agg_*`), if
  present in the CSV, are stripped with a warning naming them (per §2 —
  imports never carry composed state).
- Always produces a **flat** lattice — a re-imported composed export is a
  plain rule table whose rows happen to be combinations. Recombining is
  `AccumulatorEngine.build()`'s job, never the importer's (build/apply
  separation). The contract doc states this explicitly.
- **Sidecar format — one format, defined here.** The sidecar is always a
  `LatticeManifest` YAML (`<name>.manifest.yaml`), a babel-owned pydantic
  model with top-level keys `dimensions` (the embedded
  `DimensionsMetadata.model_dump(mode="json")` payload from the
  serialisation spec — embedded, not forked), `aggregates`
  (name + operation), and format extras as they arrive. `hit_policy`
  travels *inside* the dimensions payload (it is a `DimensionsMetadata`
  field per the hit-policies spec), not as a separate manifest key.
  `import_lattice(metadata=...)` accepts a `DimensionsMetadata` object, a
  path to a bare `DimensionsMetadata` YAML (the engine-side artefact), or a
  path to a manifest — distinguished by top-level keys. This supersedes the
  serialisation spec's brief "`<name>.metadata.yaml` sidecar" wording: the
  engine repo owns bare-metadata YAML; babel owns the manifest that wraps
  it; the shipped sidecar is the manifest. Aggregates from the manifest are
  rehydrated without the current `aggregate_columns=` manual mapping.

All behaviour in §§3–6 is **planned**, not current: today's `CsvExporter`
writes the raw frame with literal sentinel values, `CsvImporter` only
infers EXACT dimensions from `pl.read_csv`, and `RoundTripValidator` is a
warning stub. This spec defines the target contract they are rewritten to.

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
- mountainash-rules: `lattice.py` (`is_composed`),
  `accumulator_engine.py` (empty-build composed schema, per §2) + unit
  tests for both.

## Out of scope

- DMN importer (separate backlog item; round-trip stays fail-closed).
- Decomposing an imported combination table back into atomic rules
  (decomposers backlog).
- Exporting multiple partitions/lattices into one document (DRG territory,
  P2).

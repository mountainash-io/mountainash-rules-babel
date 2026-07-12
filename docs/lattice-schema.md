# Lattice Schema Contract

This document records the column taxonomy and export semantics that
mountainash-rules-babel enforces when moving lattices across format
boundaries (CSV, DMN). It documents decisions already made in the
2026-07-12 design specs; it introduces no new behaviour.

## Flat vs composed

A `Lattice` is **composed** when it came out of `AccumulatorEngine.build()`
(detected via the `__prime_product` tracking column — `Lattice.is_composed`).
Anything else — hand-built frames, imported files — is **flat**. Imports are
**always flat**: recombination is `AccumulatorEngine.build()`'s job, never an
importer's. A flat lattice that carries tracking columns is a mixed shape and
is rejected with `SchemaContractError`.

## Column taxonomy

| Column class | Pattern | Flat | Composed | Export? |
|---|---|---|---|---|
| Dimension values | `dimension_name` / `rule_field` / `range_*_field` | ✓ (authoritative) | present but **stale** (anchor rule's values, carried unchanged) — never read | flat only |
| Coalesced values | `co_<rule_field>`, `co_<range_*_field>` | ✗ | ✓ (authoritative) | composed only, emitted **under the flat names** |
| NA flags | `co_<field>_na`, `co_<dim>_na` | ✗ | ✓ | never (encoded as empty/don't-care cells) |
| Tracking | `__prime`, `__prime_product`, `__level` | ✗ | ✓ | opt-in (`include_tracking=True`) |
| Aggregates | `__agg_<name>` | ✗ | ✓ | ✓, renamed to `<name>` |
| Non-dimension passthrough | everything else except `rule_name` | ✓ (outputs, authoritative) | present but **stale** (anchor rule's values, not recomputed) | flat only |
| Identity | `rule_name` | ✓ | ✓ (anchor rule's) | ✓ flat; composed: replaced by provenance |

On a composed lattice the only meaningful per-row values are the `co_*`
columns, the tracking columns, and the `__agg_*` accumulations. Everything
else — including non-dimension "output" columns and `rule_name` — is a stale
copy from the anchor (seed) rule and must not be exported as if it described
the combination. `resolve_lattice()` in `exporters/base.py` is the single
normaliser that enforces this: every exporter reads its `LatticeView`, never
the raw frame.

## Don't-care encoding

Inside frames, don't-care is encoded **in-band** with typed sentinels
(`<NA>` / `<NOT_SET>` for strings, `-999999999` / `-999999998` for numerics,
and the temporal `UNKNOWN_DATE`/`NOT_SET_DATE` family — see
`mountainash_rules.constants.sentinels_for`). At the CSV boundary sentinels
become **empty cells** on export, and empty cells in dimension columns are
filled back to the type's UNKNOWN sentinel on import, so a CSV round trip is
lossless (`RoundTripValidator` verifies exactly this).

## Sidecar manifest

`CsvExporter` writes `<stem>.manifest.yaml` next to every CSV: a
`LatticeManifest` holding the `DimensionsMetadata` and aggregate specs.
`CsvImporter` autoloads the sidecar when no explicit metadata is passed and
rehydrates aggregates from it.

## DMN

`DmnExporter` reads the resolved view, takes `hitPolicy` from
`metadata.hit_policy` (`rule_order` → `RULE ORDER`), and fails closed with
`SchemaContractError` when asked to emit `UNIQUE` for a composed lattice —
distinct maximal combinations can overlap, so uniqueness is unproven unless
the caller passes `assume_unique=True` after a conflicts analysis.

## References

- Spec: `docs/superpowers/specs/2026-07-12-lattice-schema-contract-design.md`
- Upstream specs: `mountainash-rules/docs/superpowers/specs/` (accumulator
  correctness, serializable dimension metadata)
- Principles: `mountainash-central/01.principles/mountainash-rules/`

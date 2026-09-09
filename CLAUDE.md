# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mountain Ash Rules Babel (`mountainash_rules_babel`) is the format interchange layer for [mountainash-rules](https://github.com/mountainash-io/mountainash-rules): it imports and exports `Lattice` objects to/from external decision formats (CSV today, DMN export today; GoRules JDM and flagd/OpenFeature planned) with validation. It ships a `babel` CLI (typer).

## Architecture

### Registry + protocols

`registry.py` holds a global `registry` of exporters, importers, decomposers, and validators, keyed by name and (for importers) file extension. Components are structural `Protocol`s (`exporters/base.py`, `importers/base.py`, `validators/base.py`, `decomposers/base.py`) and are also discoverable via `mountainash_babel.*` entry points in `pyproject.toml`. Top-level API in `__init__.py`: `export_lattice`, `import_lattice`, `validate`, `decompose` (stub), `compose`/`round_trip` (NotImplemented pending the decomposition work).

### The lattice schema contract (READ `docs/lattice-schema.md` FIRST)

The core invariant of this repo. A lattice is **composed** (out of `AccumulatorEngine.build()`, detected by `Lattice.is_composed` / the `__prime_product` column) or **flat**. On a composed lattice the anchor rule's plain columns are **stale**; only `co_*` (coalesced values), `__agg_*` (aggregates), and tracking columns (`__prime`, `__prime_product`, `__level`) are meaningful.

- `exporters/base.py :: resolve_lattice(lattice, include_tracking=False) -> LatticeView` is the single normaliser: it emits authoritative values under flat names, renames `__agg_<x>` → `<x>`, drops stale/NA-flag columns, splits tracking out, and raises `SchemaContractError` on mixed shapes. **Every exporter must read a `LatticeView`, never the raw frame.**
- Don't-care values are in-band typed sentinels inside frames (`mountainash_rules.sentinels_for`) and **empty cells** at the CSV boundary (nulled on export, refilled to UNKNOWN sentinels on import).
- **Imports are always flat** — tracking columns are stripped with a `UserWarning`; recombination is `AccumulatorEngine.build()`'s job.
- `manifest.py :: LatticeManifest` (DimensionsMetadata + aggregate specs) is written as a `<stem>.manifest.yaml` sidecar by `CsvExporter` and autoloaded by `CsvImporter`.
- `DmnExporter` takes `hitPolicy` from `metadata.hit_policy` and fails closed (`SchemaContractError`) on UNIQUE for a composed lattice unless `assume_unique=True`.

### Package Structure

```
src/mountainash_rules_babel/
├── __init__.py        # public API: export_lattice, import_lattice, validate, ...
├── cli/main.py        # `babel` CLI: formats, export, import, validate
├── errors.py          # BabelError, FormatNotFoundError, ValidationError, SchemaContractError
├── manifest.py        # LatticeManifest / AggregateSpec (YAML sidecar)
├── registry.py        # component registry
├── xml_security.py    # hardened lxml parsing helpers
├── exporters/         # base (Protocol, resolve_lattice, LatticeView), csv_, dmn
├── importers/         # base (Protocol), csv_
├── validators/        # base (ValidationReport/Issue), round_trip (real for CSV),
│                      # conflicts / coverage / orphans (fail-closed stubs)
└── decomposers/       # base only (planned: hyfd FD discovery)
```

### Validators

`ValidationReport(is_valid, issues, ...)` with severity error/warning/info. `round_trip` is real for CSV (export → import → frame + metadata comparison, modulo CSV int widening); all other validators and non-CSV round-trip are **fail-closed stubs** — they return `is_valid=False` with a `not_implemented` warning. Never make a stub pass.

## Build/Test/Lint Commands

- **Tests**: `hatch run test:test-quick` (or `test:test` verbose, `test:test-cov`)
- **Single test**: `hatch run test:test-target tests/test_file.py::TestClass::test_name`
- **Lint**: `hatch run ruff:check` / `hatch run ruff:fix`
- **CLI**: `hatch run babel formats` (also export/import/validate)

**Gotcha:** the hatch env installs a NON-editable copy of `mountainash-rules`. After changing the rules repo, run `hatch env prune` here so the env rebuilds with the new code.

## Dependencies

`mountainash-rules` (sibling checkout, see hatch.toml), `polars`, `lxml`, `typer`, `pyyaml`. Optional extras: `jdm` (zen-engine), `flagd` (python-jsonlogic), `decompose` (hyfd). XML must always be parsed through `xml_security.py` helpers.

`mountainash_rules` module paths are private — import public names from the package root only (`from mountainash_rules import Lattice`).

## Code Style

Same conventions as mountainash-rules: ruff, Google docstrings, `import typing as t`, TDD (failing test first). Tests live in `tests/`; the schema-contract behaviour is specified end-to-end in `tests/test_lattice_schema_contract.py`.

## Related Documentation

- `docs/lattice-schema.md` — the schema contract (column taxonomy, don't-care encoding, sidecar, DMN rules).
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — 2026-07 lattice-schema-contract design/plan.
- `mountainash-central/01.principles/mountainash-rules-babel/` — principles (ML decomposition pipeline research context, glossary).
- `mountainash-central/04.planning/mountainash-rules-babel/a.backlog/README.md` — backlog (ML decomposition pipeline, JDM/flagd exporters, round-trip layers); see that directory's `CHANGELOG.md` for update history.

## License

Apache-2.0

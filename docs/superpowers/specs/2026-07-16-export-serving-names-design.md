# Export Serving-Consumer Names from the Package Root — Design

> **Backlog card:** mountainash-central/01.principles/mountainash-rules-babel/h.backlog/export-serving-names-from-root.md (P1)
> **Blocks:** mountainash-rules-service lattice serving (plan Task 1 Step 1 checks this)
> **Date:** 2026-07-16

## Problem

Module paths are private by ecosystem convention, but babel's root `__all__`
only exports the workflow functions. mountainash-rules-service needs
`LatticeManifest` (reads `manifest.yaml` sidecars via `from_yaml_file`,
writes fixtures via `for_lattice`).

## Decision

Export exactly `LatticeManifest` and `AggregateSpec` (both from
`manifest.py`) — `AggregateSpec` because it is the element type of
`LatticeManifest.aggregates` and callers type against it. Nothing else:
`resolve_lattice`/`LatticeView`/`SchemaContractError` have no external
consumer today (the service's storage contract moved to native snapshots),
so exporting them now would be speculative surface.

## Acceptance

- `from mountainash_rules_babel import AggregateSpec, LatticeManifest`
  works; `__all__` stays sorted; babel suite green at 81 (79 baseline + 2
  new public-api tests); no other changes.

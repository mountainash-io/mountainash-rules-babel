# Coverage Report

**Generated:** 2026-06-02
**Source hash:** 431d4500a40bb509b6fa3fb78d2e7deae6d41cdb
**Branch:** develop (working tree dirty)

## Summary

| Metric | Count |
|--------|-------|
| Modules discovered | 14 |
| Modules profiled | 14 |
| Facets written | 4 |
| Coverage gaps | 6 |

## Missing Profiles

None — all 14 discovered modules have profiles.

## Stale Profiles

None — initial profile, no previous hash to compare.

## Orphan Profiles

None — all profiles correspond to existing source files.

## Coverage Gaps

### GAP-001 — xml_security not imported by any module

**Module:** `mountainash_rules_babel.xml_security`
**Impact:** Dead code in current state. Likely prepared for future DMN importer but not wired in.
**Action:** Confirm intent — integrate into DMN exporter/importer or remove.

### GAP-002 — All 4 validators are stubs

**Modules:** `validators.conflicts`, `validators.coverage`, `validators.orphans`, `validators.round_trip`
**Impact:** `validate()` always returns `is_valid=False`. `export_lattice(validate=True)` always raises `ValidationError`.
**Action:** Implement at least `round_trip` to unblock `validate=True`, or filter stubs from default runs.

### GAP-003 — validators/coverage.py has wrong import path

**Module:** `mountainash_rules_babel.validators.coverage`
**Impact:** Silent load failure — validator disappears from registry with no user-visible error.
**Action:** Fix import from `mountainash_utils_rules.lattice` to `mountainash_rules.lattice`.

### GAP-004 — compose() and round_trip() exported but unimplemented

**Module:** `mountainash_rules_babel.__init__`
**Impact:** Users discover these via autocomplete/help but hit `NotImplementedError`.
**Action:** Remove from `__all__` until implemented, or add deprecation-style warnings.

### GAP-005 — No DMN importer exists

**Impact:** DMN export is available but import is not — no round-trip for the primary target format.
**Action:** Implement DMN importer using `xml_security.safe_parse`.

### GAP-006 — Future format extras have no implementations

**Formats:** jdm (JSON Decision Model), flagd, drools
**Impact:** Optional extras declared in `pyproject.toml` but no code exists.
**Action:** Track as planned work; document as roadmap items.

## Public Modules Without User Facet Coverage

None — all public modules appear in the users facet.

## Internal Modules Without Maintainer Facet Coverage

None — all internal modules appear in the maintainers facet.

## Low-Confidence Classifications

None — all modules classified with high confidence.

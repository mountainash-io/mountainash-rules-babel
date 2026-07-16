# Export Serving Names from Root Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from mountainash_rules_babel import AggregateSpec, LatticeManifest` works; nothing else changes.

**Architecture:** Two names re-exported from `manifest.py` into the package root `__all__`.

**Tech Stack:** n/a — import surface only.

## Global Constraints

- Repo: `/Users/nathanielramm/git/mountainash-io/mountainash-rules-babel`, branch `develop`, single commit.
- Suite: `hatch run test:test-quick` (baseline 79 passed).
- Commit trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Root export

**Files:**
- Modify: `src/mountainash_rules_babel/__init__.py`
- Test: `tests/test_public_api.py` (create if absent)

**Interfaces:**
- Produces: root-importable `LatticeManifest`, `AggregateSpec`. Consumed by mountainash-rules-service lattice-serving plan (Task 1 Step 1 prerequisite check).

- [ ] **Step 1: Write the failing test**

Create (or append to) `tests/test_public_api.py`:

```python
"""Root import surface: names consumers may rely on."""


def test_serving_names_importable_from_root():
    from mountainash_rules_babel import AggregateSpec, LatticeManifest

    assert hasattr(LatticeManifest, "from_yaml_file")
    assert hasattr(LatticeManifest, "for_lattice")
    assert AggregateSpec(column_name="discount").operation == "sum"


def test_names_in_dunder_all():
    import mountainash_rules_babel as babel

    assert "LatticeManifest" in babel.__all__
    assert "AggregateSpec" in babel.__all__
    assert list(babel.__all__) == sorted(babel.__all__, key=str.lower)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/nathanielramm/git/mountainash-io/mountainash-rules-babel && hatch run test:test-target tests/test_public_api.py -v`
Expected: FAIL — `ImportError: cannot import name 'AggregateSpec'`.

- [ ] **Step 3: Implement**

In `src/mountainash_rules_babel/__init__.py`, add with the other package imports:

```python
from mountainash_rules_babel.manifest import AggregateSpec, LatticeManifest
```

and extend `__all__` (keep case-insensitive sort):

```python
__all__ = (
    "__version__",
    "AggregateSpec",
    "compose",
    "decompose",
    "export_lattice",
    "import_lattice",
    "LatticeManifest",
    "round_trip",
    "validate",
)
```

Note: `manifest.py` imports from `mountainash_rules` at module top — already a hard dependency (no circularity; verify the suite stays green).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/nathanielramm/git/mountainash-io/mountainash-rules-babel && hatch run test:test-quick && hatch run ruff:check`
Expected: 81 passed (79 + 2); ruff has 4 pre-existing errors (1 F401 `__init__.py`, 3 E402 `exporters/base.py`) — no NEW errors; the added import must not introduce an F401 (it won't: `__all__` references it).

- [ ] **Step 5: Commit, push, flip the card**

```bash
cd /Users/nathanielramm/git/mountainash-io/mountainash-rules-babel
git add src/mountainash_rules_babel/__init__.py tests/test_public_api.py
git commit -m "feat: export LatticeManifest + AggregateSpec from package root

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push
```

Flip `mountainash-central/.../mountainash-rules-babel/h.backlog/export-serving-names-from-root.md` to DONE with the commit ref; the rules-service lattice-serving plan's prerequisite is now satisfied.

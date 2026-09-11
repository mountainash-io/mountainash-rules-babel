---
title: "Chapter 2: Python Plugin Infrastructure"
description: "Python protocols, runtime_checkable, entry points, and the PluginRegistry class that powers babel's plugin system."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 2: Python Plugin Infrastructure

## Summary

This chapter covers the Python language features that enable the babel plugin system. You will learn about Python protocols and the runtime_checkable decorator, the entry points mechanism from importlib.metadata, and how the PluginRegistry class discovers and loads plugins at runtime through auto-discovery.

---

## Why a Plugin Architecture?

Babel must support multiple input formats, multiple output formats, multiple validators, and multiple decomposition strategies. Hard-coding these into a monolithic module would make the system rigid and difficult to extend. A plugin architecture allows new capabilities to be added --- by the core team or by third parties --- without modifying existing code. Python provides two key mechanisms that make this possible: **protocols** for defining contracts, and **entry points** for discovering implementations at runtime.

<!-- concept:7 -->
<!-- concept:8 -->
## Python Protocols

A **protocol** in Python is a structural typing mechanism introduced in PEP 544 (Python 3.8+). Unlike abstract base classes, protocols define a contract based on what methods and attributes an object has, rather than what class hierarchy it inherits from. Any class that implements the required methods and attributes satisfies the protocol, without needing to explicitly inherit from it.

In babel, protocols define the contracts that all plugins must follow. The `Importer` protocol, for example, declares that any importer must have a `name` attribute, a `file_extensions` attribute, and an `import_lattice` method. Here is the actual protocol definition from the codebase:

```python
from typing import Protocol, runtime_checkable
from pathlib import Path
from mountainash_rules.lattice import Lattice

@runtime_checkable
class Importer(Protocol):
    name: str
    file_extensions: list[str]

    def import_lattice(self, path: Path, **options) -> Lattice: ...
```

The `...` (ellipsis) in the method body indicates that this is a protocol definition, not an implementation. Any class that provides `name`, `file_extensions`, and `import_lattice` with compatible signatures satisfies this protocol --- even if it has never heard of the `Importer` class.

Protocols enable **structural subtyping** (also called "duck typing with type checking"). This matters for babel because:

- Plugin authors do not need to import or inherit from babel's base classes
- Type checkers (mypy, pyright) can verify plugin conformance at static analysis time
- The system is open to extension without requiring modification of existing code

#### Diagram: Protocol vs. ABC Comparison

<iframe src="../../sims/protocol-vs-abc/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>Protocol vs. ABC Comparison</summary>
Type: diagram
**sim-id:** protocol-vs-abc<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Compare Python protocols (structural typing) with abstract base classes (nominal typing) to show why babel uses protocols.

**Components:** Two parallel hierarchies. Left side: ABC approach with explicit inheritance arrows (CsvImporter inherits from AbstractImporter). Right side: Protocol approach showing CsvImporter independently satisfying the Importer protocol via matching interface (dashed conformance arrow). Center annotation highlights "no inheritance required."

**Interactions:** Click either approach to highlight its relationship arrows. Hover over nodes to see pros/cons tooltip. Toggle button switches between "type checker view" and "runtime view."

**Colors:** Protocol nodes in steel blue, ABC nodes in gray, implementation classes in dark green, conformance arrows dashed in teal.

**Learning Objective:** Compare structural and nominal typing approaches for plugin contracts (Bloom: Analyze).
</details>

## Runtime Checkable Protocol

By default, Python protocols are a static analysis construct --- they help type checkers but have no effect at runtime. The `@runtime_checkable` decorator changes this by enabling `isinstance()` checks against the protocol at runtime.

```python
@runtime_checkable
class Importer(Protocol):
    name: str
    file_extensions: list[str]
    def import_lattice(self, path: Path, **options) -> Lattice: ...
```

With `@runtime_checkable` applied, you can write:

```python
obj = CsvImporter()
assert isinstance(obj, Importer)  # True at runtime
```

This capability is critical for the PluginRegistry. When the registry discovers a plugin via entry points, it instantiates the class and can verify that the object actually satisfies the expected protocol. If a third-party plugin is missing a required method, the registry can detect this immediately rather than failing later during a translation operation.

There is an important limitation: `@runtime_checkable` only checks that methods and attributes **exist** on the object. It does not verify signatures, return types, or attribute types. Full signature conformance is verified only by static type checkers.

| Check Type | What It Verifies | When It Runs |
|-----------|------------------|--------------|
| Static (mypy/pyright) | Method signatures, return types, attribute types | During development |
| Runtime (`isinstance`) | Methods and attributes exist | During plugin discovery |
| Neither | Semantic correctness (e.g., returns valid Lattice) | Must be tested |

<!-- concept:9 -->
<!-- concept:13 -->
## Entry Points Mechanism

Python's **entry points mechanism** (defined in `importlib.metadata`) allows installed packages to advertise components that other packages can discover without knowing the package name in advance. Entry points are declared in a package's `pyproject.toml` and become available to any Python process that queries for them.

The mechanism works in three steps:

1. A package declares entry points in its `pyproject.toml` under `[project.entry-points."group_name"]`
2. When the package is installed, the packaging tool (pip, uv, hatch) records these entry points in the package metadata
3. At runtime, any code can call `importlib.metadata.entry_points(group="group_name")` to discover all registered entry points in that group

Here is how babel's built-in exporters are declared in `pyproject.toml`:

```toml
[project.entry-points."mountainash_babel.exporters"]
csv = "mountainash_rules_babel.exporters.csv_:CsvExporter"
dmn = "mountainash_rules_babel.exporters.dmn:DmnExporter"
```

Each line maps a short name (e.g., `csv`) to a fully-qualified Python path pointing to a class. When babel calls `importlib.metadata.entry_points(group="mountainash_babel.exporters")`, it receives both entries. It can then call `.load()` on each entry point to import and instantiate the class.

The entry points mechanism is what makes babel truly extensible. A third-party package can declare its own entry points in the same group, and babel will discover them automatically --- no configuration changes needed in the core babel package.

<!-- concept:12 -->
#### Diagram: Entry Point Discovery Flow

<iframe src="../../sims/entry-point-discovery/main.html" width="100%" height="500px" scrolling="no"></iframe>
<details markdown="1">
<summary>Entry Point Discovery Flow</summary>
Type: workflow
**sim-id:** entry-point-discovery<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Trace the journey from pyproject.toml declaration through package installation to runtime discovery.

**Components:** Sequential nodes: pyproject.toml (declaration), Package Install (uv/pip), Package Metadata (dist-info), importlib.metadata.entry_points() call, EntryPoint objects, .load() call, Plugin Instance. Arrows show the data flow at each stage.

**Interactions:** Click each node to see a code snippet or file content example for that stage. Hover for timing information (install-time vs. runtime). Animated arrow pulses show the discovery sequence when "Play" button is clicked.

**Colors:** Install-time nodes in gold, runtime nodes in steel blue, code snippets in dark background panels.

**Learning Objective:** Trace the complete path from entry point declaration to runtime plugin instantiation (Bloom: Apply).
</details>

<!-- concept:11 -->
## PluginRegistry Class

The **PluginRegistry** class is the central coordinator that discovers, stores, and provides access to all babel plugins. It maintains four internal dictionaries --- one for each plugin category (exporters, importers, decomposers, validators) --- and provides typed accessor methods for retrieving plugins by name.

The class is defined in `mountainash_rules_babel/registry.py`. Its constructor accepts an `auto_discover` parameter that defaults to `True`, meaning plugins are discovered immediately upon instantiation:

```python
class PluginRegistry:
    def __init__(self, auto_discover: bool = True) -> None:
        self._exporters: dict[str, Exporter] = {}
        self._importers: dict[str, Importer] = {}
        self._decomposers: dict[str, Decomposer] = {}
        self._validators: dict[str, Validator] = {}
        if auto_discover:
            self.discover()
```

The registry provides two ways to populate itself:

- **Auto-discovery** via entry points (the `discover()` method)
- **Manual registration** via `register_exporter()`, `register_importer()`, etc.

Manual registration is useful for testing, where you want to inject mock plugins, or for applications that need to register plugins that are not installed as packages.

The retrieval methods (`get_exporter`, `get_importer`, etc.) raise a `FormatNotFoundError` if the requested plugin name does not exist. This provides clear error messages that list all available plugins, helping users diagnose configuration issues.

A module-level singleton instance is created at import time:

```python
registry = PluginRegistry(auto_discover=True)
```

This singleton is used throughout babel's public API (`export_lattice`, `import_lattice`, `validate`) and by the CLI module.

## Auto Discovery

**Auto discovery** is the process by which the PluginRegistry finds and loads all available plugins without explicit configuration. The `discover()` method iterates over the four entry point groups, loads each entry point, instantiates the class, and stores the resulting object in the appropriate dictionary.

The discovery algorithm is straightforward but includes error handling to ensure that one broken plugin does not prevent others from loading:

```python
def discover(self) -> None:
    for category, group in _ENTRY_POINT_GROUPS.items():
        for ep in importlib.metadata.entry_points(group=group):
            try:
                cls = ep.load()
                instance = cls()
                if category == "exporter":
                    self._exporters[ep.name] = instance
                elif category == "importer":
                    self._importers[ep.name] = instance
                # ... similar for decomposer, validator
            except Exception as exc:
                logger.debug("Failed to load %s plugin '%s': %s",
                             category, ep.name, exc)
```

Key design decisions in this implementation:

- **Fail gracefully** --- if a plugin raises an exception during import or instantiation, it is logged at DEBUG level and skipped. The remaining plugins still load.
- **Name comes from entry point** --- the `ep.name` (from pyproject.toml) is used as the dictionary key, not the class's `name` attribute. This means the pyproject.toml declaration is the single source of truth for plugin naming.
- **Instantiation at discovery time** --- plugins are instantiated once during discovery and reused for all subsequent operations. This avoids repeated import and construction costs.

## Entry Point Groups

An **entry point group** is a namespace that categorizes related entry points. Babel defines four groups, each corresponding to one plugin axis:

| Group Name | Plugin Type | Purpose |
|-----------|-------------|---------|
| `mountainash_babel.exporters` | Exporter | Convert Lattice to output format |
| `mountainash_babel.importers` | Importer | Parse input format into Lattice |
| `mountainash_babel.decomposers` | Decomposer | Split complex tables into fragments |
| `mountainash_babel.validators` | Validator | Check Lattice for logical issues |

These group names are defined in the `_ENTRY_POINT_GROUPS` dictionary at the top of `registry.py`:

```python
_ENTRY_POINT_GROUPS: dict[str, str] = {
    "exporter": "mountainash_babel.exporters",
    "importer": "mountainash_babel.importers",
    "decomposer": "mountainash_babel.decomposers",
    "validator": "mountainash_babel.validators",
}
```

The naming convention uses a dotted namespace (`mountainash_babel.exporters`) to avoid collisions with entry point groups from unrelated packages. Any installed package that declares entry points in one of these groups will have its plugins discovered by babel.

#### Diagram: Plugin Registry Architecture

<iframe src="../../sims/plugin-registry-architecture/main.html" width="100%" height="500px" scrolling="no"></iframe>
<details markdown="1">
<summary>Plugin Registry Architecture</summary>
Type: infographic
**sim-id:** plugin-registry-architecture<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show the complete architecture of the PluginRegistry, its four dictionaries, the entry point groups feeding into them, and the public API methods that consume them.

**Components:** Central PluginRegistry node connected to four dictionary nodes (exporters, importers, decomposers, validators). Each dictionary is fed by an entry point group node. On the right, public API methods (get_exporter, get_importer, list_exporters, etc.) connect to the appropriate dictionary. Error path shows FormatNotFoundError.

**Interactions:** Click a dictionary node to see its current contents (the built-in plugins). Click an API method to trace its call path through the registry. Hover over entry point group nodes to see example pyproject.toml declarations.

**Colors:** Registry in dark slate blue, dictionaries in teal, entry point groups in gold, API methods in dark green, error paths in crimson.

**Learning Objective:** Evaluate how the registry coordinates discovery, storage, and retrieval of plugins (Bloom: Evaluate).
</details>

The separation into four groups enables independent extension. A package that provides only a new exporter need not implement validators or decomposers. Similarly, a validation-focused package can register validators without touching the import/export pipeline.

## Key Takeaways

- **Python protocols** define plugin contracts through structural typing, allowing any class with the right methods to satisfy the contract without inheritance.
- **The `@runtime_checkable` decorator** enables `isinstance()` checks at runtime, allowing the registry to verify plugin conformance during discovery.
- **Entry points** are a packaging-level mechanism that lets installed packages advertise components for discovery by other packages, without requiring any import-time coupling.
- **The PluginRegistry class** maintains four dictionaries (exporters, importers, decomposers, validators) and provides typed get/list methods with clear error messages.
- **Auto discovery** iterates over entry point groups at registry instantiation, loading and instantiating all advertised plugins while gracefully handling failures.
- **Entry point groups** are namespaced identifiers (e.g., `mountainash_babel.exporters`) that categorize plugins by function and prevent collisions with unrelated packages.
- A **module-level singleton** (`registry`) provides a shared instance used by babel's public API and CLI.

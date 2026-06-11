---
title: "Chapter 3: Plugin Extension Points and Error Handling"
description: "The four plugin axes (exporters, importers, decomposers, validators) registered via entry points, plus the BabelError exception hierarchy."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 3: Plugin Extension Points and Error Handling

## Summary

This chapter explains how the four plugin extension axes --- exporters, importers, decomposers, and validators --- are registered via entry point groups. It also introduces the BabelError exception hierarchy that provides structured error reporting across all plugin operations.

---

<!-- concept:14 -->
<!-- concept:15 -->
<!-- concept:16 -->
<!-- concept:17 -->
## Extension Points as a Design Pattern

An **extension point** is a well-defined location in a system where new functionality can be plugged in. In babel, there are exactly four extension points, each corresponding to one stage of the decision table lifecycle: importing data into the system, exporting it to a target format, validating it for correctness, and decomposing it into normalized fragments. Each extension point is backed by a protocol (the contract), an entry point group (the registration mechanism), and a dictionary in the PluginRegistry (the runtime storage).

This chapter examines each extension point in detail and then introduces the error handling infrastructure that unifies error reporting across all four.

## Exporter Entry Points

The **exporter entry point group** (`mountainash_babel.exporters`) is where output format plugins register themselves. An exporter is responsible for converting a Lattice object into a specific file format --- CSV, DMN XML, or any format a third-party plugin might implement.

The current built-in exporters are declared in `pyproject.toml`:

```toml
[project.entry-points."mountainash_babel.exporters"]
csv = "mountainash_rules_babel.exporters.csv_:CsvExporter"
dmn = "mountainash_rules_babel.exporters.dmn:DmnExporter"
```

Each entry maps a short name to a class path. The short name (`csv`, `dmn`) becomes the identifier users pass to the CLI (`--format csv`) or the Python API (`export_lattice(lattice, "dmn")`). When the PluginRegistry discovers these entry points, it loads each class, instantiates it, and stores the instance in its `_exporters` dictionary keyed by that short name.

To create a third-party exporter, a developer would:

1. Implement a class satisfying the Exporter protocol (providing `name`, `file_extension`, `export`, and `export_bytes`)
2. Declare the class in their own package's `pyproject.toml` under the same group
3. Install the package --- babel's auto-discovery will find and load it automatically

This design means the core babel package never needs to be modified or even aware of third-party exporters.

## Importer Entry Points

The **importer entry point group** (`mountainash_babel.importers`) registers plugins that parse external file formats into Lattice objects. Currently, babel ships with a single importer:

```toml
[project.entry-points."mountainash_babel.importers"]
csv = "mountainash_rules_babel.importers.csv_:CsvImporter"
```

The registry also provides a convenience method, `get_importer_for_extension()`, that finds an importer by file extension rather than by name. This enables the CLI's format auto-detection: when a user provides `--input rules.csv` without specifying `--format`, babel examines the `.csv` extension and routes to the appropriate importer.

The importer discovery process mirrors the exporter process exactly:

- Entry points are loaded from the `mountainash_babel.importers` group
- Each class is instantiated and stored in `_importers`
- Retrieval by name uses `get_importer(name)`
- Retrieval by extension uses `get_importer_for_extension(ext)`

#### Diagram: Extension Point Registration Flow

<iframe src="../../sims/extension-point-registration/main.html" width="100%" height="500px" scrolling="no"></iframe>
<details markdown="1">
<summary>Extension Point Registration Flow</summary>
Type: workflow
**sim-id:** extension-point-registration<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show how a plugin class goes from pyproject.toml declaration through the entry point group to the PluginRegistry dictionary, and finally to user-facing API access.

**Components:** Four parallel swim lanes (one per extension point type: exporter, importer, decomposer, validator). Each lane shows: pyproject.toml entry, entry_points() call, .load() and instantiation, dictionary storage, get_*() retrieval. A "third-party package" node shows how external plugins feed into the same groups.

**Interactions:** Click a swim lane to highlight only that extension point's flow. Hover over the "third-party package" node to see an example pyproject.toml declaration for a hypothetical JSON exporter. Drag nodes to rearrange.

**Colors:** Exporter lane in crimson, Importer lane in dark green, Decomposer lane in teal, Validator lane in gold. Third-party nodes shown with dashed borders.

**Learning Objective:** Apply the entry point registration pattern to a new plugin type (Bloom: Apply).
</details>

## Decomposer Entry Points

The **decomposer entry point group** (`mountainash_babel.decomposers`) registers plugins that split large or complex decision tables into smaller, normalized fragments. Decomposition is useful when a single table combines multiple independent concerns (e.g., geographic rules mixed with product-line rules) that would be cleaner as separate tables.

Currently, no built-in decomposers are shipped with babel (the `pyproject.toml` does not declare entries in this group), but the infrastructure is in place. The Decomposer protocol requires:

- A `name` attribute identifying the decomposition strategy
- A `decompose(lattice, **options)` method that returns a `DecompositionResult`

Third-party packages can register decomposers using:

```toml
[project.entry-points."mountainash_babel.decomposers"]
hyfd = "my_package.decomposers:HyFDDecomposer"
```

The registry will discover and load them via the same auto-discovery mechanism.

## Validator Entry Points

The **validator entry point group** (`mountainash_babel.validators`) registers plugins that check a Lattice for logical issues. Babel ships with four built-in validators:

```toml
[project.entry-points."mountainash_babel.validators"]
round_trip = "mountainash_rules_babel.validators.round_trip:RoundTripValidator"
conflicts = "mountainash_rules_babel.validators.conflicts:ConflictsValidator"
coverage = "mountainash_rules_babel.validators.coverage:CoverageValidator"
orphans = "mountainash_rules_babel.validators.orphans:OrphansValidator"
```

Each validator examines a different aspect of the decision table:

| Validator | What It Checks |
|-----------|---------------|
| `conflicts` | Overlapping rules that produce different outputs for the same input |
| `coverage` | Gaps in the input space where no rule applies |
| `orphans` | Rules that can never fire because they are shadowed by other rules |
| `round_trip` | Whether exporting and re-importing produces identical data |

Validators are designed to be composable. The `validate()` public API function accepts an optional `checks` parameter to select specific validators, or runs all registered validators when no selection is provided. This allows users to run a quick single-check or a comprehensive audit depending on their needs.

<!-- concept:68 -->
## The BabelError Exception Hierarchy

All exceptions raised by babel operations derive from a single base class, **BabelError**. This provides a clean hierarchy that calling code can catch at the appropriate level of granularity --- catch `BabelError` for any babel-related failure, or catch a specific subclass for targeted error handling.

The error hierarchy is defined in `mountainash_rules_babel/errors.py`:

```python
class BabelError(Exception):
    pass

class FormatNotFoundError(BabelError):
    def __init__(self, format_name: str, available: list[str] | None = None):
        ...

class ImportError_(BabelError):
    pass

class ExportError(BabelError):
    pass

class DecompositionError(BabelError):
    pass

class ValidationError(BabelError):
    def __init__(self, message: str, report: ValidationReport | None = None):
        ...

class DependencyMissingError(BabelError, ImportError):
    pass
```

The base class carries no additional logic beyond being a distinct exception type. All babel-specific errors inherit from it, which means application code can use a single `except BabelError` clause to handle any babel failure generically, while more specific handlers can target individual error types.

#### Diagram: BabelError Exception Hierarchy

<iframe src="../../sims/babel-error-hierarchy/main.html" width="100%" height="400px" scrolling="no"></iframe>
<details markdown="1">
<summary>BabelError Exception Hierarchy</summary>
Type: diagram
**sim-id:** babel-error-hierarchy<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Visualize the inheritance tree of babel's exception classes, showing which errors are raised in which contexts.

**Components:** Tree layout with BabelError at root. Children: FormatNotFoundError, ImportError_, ExportError, DecompositionError, ValidationError, DependencyMissingError. Each node annotated with the context in which it is raised (e.g., "raised by get_exporter when name not found").

**Interactions:** Click any error class to see its constructor signature and an example of code that raises it. Hover for a tooltip showing when to catch this specific error vs. the base class.

**Colors:** BabelError in orange, registry errors in crimson, operation errors in dark green, validation errors in gold.

**Learning Objective:** Evaluate which exception to catch for different error handling scenarios (Bloom: Evaluate).
</details>

<!-- concept:69 -->
## FormatNotFoundError

The **FormatNotFoundError** is the most commonly encountered error in babel. It is raised whenever a user requests a plugin by name or file extension that does not exist in the registry. The error class carries two pieces of diagnostic information:

- `format_name` --- the name or extension that was requested
- `available` --- a list of all registered alternatives

The error message is constructed to be immediately actionable:

```python
class FormatNotFoundError(BabelError):
    def __init__(self, format_name: str, available: list[str] | None = None) -> None:
        self.format_name = format_name
        self.available = available or []
        available_str = ", ".join(self.available) if self.available else "none"
        super().__init__(
            f"Format '{format_name}' not found. Available formats: {available_str}"
        )
```

This produces messages like:

```
Format 'json' not found. Available formats: csv, dmn
```

The error is raised in four locations within the PluginRegistry:

- `get_exporter(name)` --- when the exporter name is not registered
- `get_importer(name)` --- when the importer name is not registered
- `get_decomposer(name)` --- when the decomposer name is not registered
- `get_importer_for_extension(ext)` --- when no importer supports the given file extension

!!! tip "Handling FormatNotFoundError in Application Code"
    When building applications on top of babel, catch `FormatNotFoundError` specifically to provide users with guidance. The `available` attribute on the exception gives you the data needed to suggest valid alternatives or to present a selection dialog.

## Connecting Extension Points to Error Handling

The relationship between extension points and error handling follows a consistent pattern. Every retrieval method in the registry raises `FormatNotFoundError` with a populated `available` list when the requested plugin is not found. This means error handling is not an afterthought --- it is an integral part of the extension point design.

The pattern ensures that:

- Users always know what went wrong (the requested name/extension)
- Users always know what they can do instead (the available alternatives)
- Application code can programmatically inspect available options via the exception attributes
- The error path is identical regardless of which extension point was queried

#### Diagram: Four Extension Points Overview

<iframe src="../../sims/four-extension-points/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>Four Extension Points Overview</summary>
Type: infographic
**sim-id:** four-extension-points<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Provide a unified view of all four extension points, their protocols, their entry point groups, and the error handling that connects them.

**Components:** Four quadrants arranged around a central Lattice node. Top-left: Importers (produces Lattice). Top-right: Exporters (consumes Lattice). Bottom-left: Validators (inspects Lattice). Bottom-right: Decomposers (transforms Lattice). Each quadrant shows its protocol, entry point group name, and registered plugins. FormatNotFoundError node connects to all four quadrants.

**Interactions:** Click any quadrant to expand it showing the full protocol definition and registered entry points. Hover over the central Lattice to see data flow directions. Click FormatNotFoundError to see example error messages for each extension point.

**Colors:** Importers in dark green, Exporters in crimson, Validators in gold, Decomposers in teal, Lattice in steel blue, errors in orange.

**Learning Objective:** Synthesize how the four extension points work together around the Lattice object (Bloom: Synthesize).
</details>

## Key Takeaways

- **Exporter entry points** register output format plugins under the `mountainash_babel.exporters` group; the short name becomes the user-facing format identifier.
- **Importer entry points** register input format plugins under `mountainash_babel.importers`, with an additional extension-based lookup for auto-detection.
- **Decomposer entry points** register table-splitting strategies under `mountainash_babel.decomposers`; the infrastructure is ready for third-party implementations.
- **Validator entry points** register quality checks under `mountainash_babel.validators`; four built-in validators cover conflicts, coverage, orphans, and round-trip integrity.
- **BabelError** is the common base exception for all babel operations, enabling both coarse-grained and fine-grained error handling.
- **FormatNotFoundError** provides actionable diagnostics by including the requested name and all available alternatives in the error message.
- The extension point design ensures that adding new formats, validators, or decomposers never requires modifying the babel core package.

---
title: "Chapter 5: Exporter Architecture"
description: "The Exporter protocol and its two implementations: CsvExporter with Polars DataFrame conversion and DmnExporter for DMN XML generation."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 5: Exporter Architecture

## Summary

This chapter introduces the Exporter protocol and its two concrete implementations --- CsvExporter and DmnExporter. You will learn the protocol contract (name, file extension, export, export_bytes), how CsvExporter uses Polars DataFrame conversion, and the foundational setup of the DmnExporter including its relationship to the DMN standard.

## Concepts Covered

- Exporter Protocol
- Export Name Attribute
- File Extension Attribute
- Export Method
- Export Bytes Method
- CsvExporter Class
- Polars DataFrame Conversion
- DmnExporter Class

## Prerequisites

- Chapter 1: Foundations (CSV Format, XML Format, DMN Standard, Lattice Object)
- Chapter 2: Python Plugin Infrastructure (Runtime Checkable Protocol)
- Chapter 3: Plugin Extension Points (Exporter Entry Points)

---

<!-- concept:26 -->
<!-- concept:27 -->
<!-- concept:29 -->
<!-- concept:30 -->
## The Exporter's Role

Exporters occupy the output side of the babel pipeline. They consume a Lattice object and produce a file or byte stream in a specific format. While importers must deal with ambiguity (inferring metadata from schema-less formats), exporters have the opposite challenge: they must faithfully serialize all the semantic information in the Lattice into a format that target systems can consume.

## Exporter Protocol

The **Exporter protocol** defines the contract that all exporter plugins must satisfy. It is declared in `mountainash_rules_babel/exporters/base.py`:

```python
@runtime_checkable
class Exporter(Protocol):
    name: str
    file_extension: str

    def export(self, lattice: Lattice, path: Path, **options) -> Path: ...
    def export_bytes(self, lattice: Lattice, **options) -> bytes: ...
```

Compared to the Importer protocol (two attributes, one method), the Exporter protocol has two attributes and two methods. The dual-method design reflects two common usage patterns: writing to a file on disk and generating bytes in memory for network transmission or further processing.

Note the subtle difference in attribute naming: importers use `file_extensions` (plural, a list) because an importer might handle multiple extensions, while exporters use `file_extension` (singular, a string) because each exporter produces exactly one output format.

<!-- concept:28 -->
## Export Name Attribute

The **export name attribute** identifies the exporter within the registry. Users reference this name in the CLI (`--format dmn`) and the Python API (`export_lattice(lattice, "dmn")`). The name must be unique across all registered exporters.

The built-in exporters use short, lowercase names:

- `"csv"` for the CsvExporter
- `"dmn"` for the DmnExporter

## File Extension Attribute

The **file extension attribute** specifies the file extension that this exporter produces. It includes the leading dot:

```python
class CsvExporter:
    file_extension: str = ".csv"

class DmnExporter:
    file_extension: str = ".dmn"
```

The extension is used by the CLI when constructing output file names and by the `formats` command to display available output formats alongside their extensions.

| Attribute | Type | Importer Equivalent | Difference |
|-----------|------|-------------------|------------|
| `name` | `str` | `name` | Same purpose |
| `file_extension` | `str` | `file_extensions` | Singular vs. plural (one output format per exporter) |

## Export Method

The **export method** writes a Lattice to a file at the specified path and returns the path. This is the primary method for CLI and batch operations where the output goes to disk:

```python
def export(self, lattice: Lattice, path: Path, **options) -> Path: ...
```

The method accepts the same `**options` pattern as the importer, allowing format-specific parameters. The DmnExporter, for example, accepts `decision_name` and `table_name` options that control the identifiers in the generated XML.

Returning the `Path` object allows callers to chain operations:

```python
output_path = exporter.export(lattice, Path("output.dmn"),
                               decision_name="PricingDecision")
print(f"Exported to {output_path}")
```

## Export Bytes Method

The **export_bytes method** produces the same output as `export` but returns it as a `bytes` object instead of writing to a file:

```python
def export_bytes(self, lattice: Lattice, **options) -> bytes: ...
```

This method enables scenarios where the output is consumed in memory:

- Streaming the output as an HTTP response in a web service
- Piping the output to another process
- Comparing export output in tests without touching the filesystem
- Storing the output in a database or message queue

The two export methods share the same serialization logic. In practice, both built-in exporters implement `export` by calling `export_bytes` and writing the result to disk, or vice versa, to avoid duplicating the conversion code.

#### Diagram: Exporter Dual Interface

<iframe src="../../sims/exporter-dual-interface/main.html" width="100%" height="400px" scrolling="no"></iframe>
<details markdown="1">
<summary>Exporter Dual Interface</summary>
Type: diagram
**sim-id:** exporter-dual-interface<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show how the export() and export_bytes() methods relate to each other and to the different consumption patterns (file, HTTP, test, database).

**Components:** Center: Exporter node with two method ports (export, export_bytes). Left: Lattice input. Right-top: File System path (export method target). Right-bottom: four consumption nodes for bytes (HTTP Response, Pipe, Test Assertion, Database). Internal arrow shows DmnExporter's delegation from export to export_bytes.

**Interactions:** Click export() to highlight the file-based flow. Click export_bytes() to highlight the in-memory flow. Hover over consumption nodes for usage example tooltips.

**Colors:** Exporter in crimson, Lattice in steel blue, file system in gold, in-memory consumers in teal.

**Learning Objective:** Evaluate when to use export() vs. export_bytes() based on the consumption context (Bloom: Evaluate).
</details>

<!-- concept:31 -->
<!-- concept:33 -->
## CsvExporter Class

The **CsvExporter** converts a Lattice back into CSV format. It is the simplest exporter because CSV is a flat, text-based format that closely mirrors the Lattice's internal DataFrame structure.

```python
class CsvExporter:
    name: str = "csv"
    file_extension: str = ".csv"

    def export(self, lattice: Lattice, path: Path, **options) -> Path:
        path = Path(path)
        df = self._to_polars(lattice)
        df.write_csv(path)
        return path

    def export_bytes(self, lattice: Lattice, **options) -> bytes:
        df = self._to_polars(lattice)
        csv_str = df.write_csv()
        return csv_str.encode("utf-8") if isinstance(csv_str, str) else csv_str
```

Both methods delegate to a private `_to_polars` helper that handles the Lattice-to-DataFrame conversion. The `export` method writes directly to a file, while `export_bytes` writes to a string and encodes it as UTF-8 bytes.

The CsvExporter does not include dimension metadata, match strategies, or aggregation information in the output --- CSV has no way to represent these. This means a round-trip (CSV import followed by CSV export) preserves the data but loses metadata, which is why the RoundTripValidator exists as a separate validation check.

<!-- concept:32 -->
## Polars DataFrame Conversion

The **Polars DataFrame conversion** step extracts a `pl.DataFrame` from the Lattice's `combinations` property. The Lattice stores its data in a backend-agnostic way, so the conversion must handle multiple possible storage formats:

```python
def _to_polars(self, lattice: Lattice) -> pl.DataFrame:
    combos = lattice.combinations
    if isinstance(combos, pl.DataFrame):
        return combos
    try:
        from mountainash.relations import relation
        return relation(combos).to_polars()
    except Exception:
        raise TypeError(f"Cannot convert {type(combos)} to polars DataFrame")
```

The conversion follows a three-step fallback strategy:

1. **Direct check** --- if `combinations` is already a Polars DataFrame, return it immediately (zero-cost path)
2. **Relation API** --- attempt to convert through the mountainash relations abstraction, which handles Ibis backends and other query engines
3. **Failure** --- raise a `TypeError` with a diagnostic message if neither approach works

This pattern allows the CsvExporter (and the DmnExporter, which uses an identical `_to_polars` function) to work with Lattice objects regardless of their internal storage backend.

## DmnExporter Class

The **DmnExporter** converts a Lattice into a DMN 1.3 XML document. It is significantly more complex than the CsvExporter because DMN XML has a hierarchical structure with namespaces, type annotations, and FEEL expressions.

The class follows the same protocol interface:

```python
class DmnExporter:
    name: str = "dmn"
    file_extension: str = ".dmn"

    def export(self, lattice: Lattice, path: Path, **options) -> Path:
        path = Path(path)
        data = self.export_bytes(lattice, **options)
        path.write_bytes(data)
        return path

    def export_bytes(self, lattice: Lattice, **options) -> bytes:
        decision_name = options.get("decision_name", "GeneratedDecision")
        table_name = options.get("table_name", "GeneratedTable")
        # ... XML construction logic
```

The DmnExporter accepts two format-specific options through `**options`:

- **decision_name** --- the human-readable name for the DMN decision element (defaults to `"GeneratedDecision"`)
- **table_name** --- the identifier for the decision table element (defaults to `"GeneratedTable"`)

The `export` method delegates entirely to `export_bytes` and writes the resulting bytes to disk. This keeps the serialization logic in one place and ensures that file-based and in-memory exports always produce identical output.

The DmnExporter uses the **lxml** library to construct the XML tree. The namespace constant and default namespace map are defined at module level:

```python
DMN_NS = "https://www.omg.org/spec/DMN/20191111/MODEL/"
NSMAP = {None: DMN_NS}
```

The `None` key in `NSMAP` sets the default namespace, so elements are created without a prefix (e.g., `<definitions>` rather than `<dmn:definitions>`). This matches the canonical DMN XML format expected by most decision engines.

#### Diagram: DmnExporter Internal Architecture

<iframe src="../../sims/dmn-exporter-architecture/main.html" width="100%" height="500px" scrolling="no"></iframe>
<details markdown="1">
<summary>DmnExporter Internal Architecture</summary>
Type: workflow
**sim-id:** dmn-exporter-architecture<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show the internal stages of the DmnExporter's export_bytes method, from option parsing through Lattice unpacking, XML tree construction, and final serialization.

**Components:** Sequential stages: Options Parsing (decision_name, table_name), Polars Conversion (_to_polars), Column Classification (dimensions vs. outputs), XML Tree Construction (definitions, decision, decisionTable, inputs, outputs, rules), FEEL Expression Mapping (per cell), XML Serialization (etree.tostring). Each stage has input/output annotations.

**Interactions:** Click any stage to see the corresponding code from dmn.py. Hover for timing information (which stages are O(1) vs. O(n) where n = number of rows). Animated flow traces a single row from DataFrame through to XML rule element.

**Colors:** Parsing stages in gold, conversion stages in teal, XML construction in crimson, serialization in dark blue.

**Learning Objective:** Trace the complete DMN export pipeline from Lattice to XML bytes (Bloom: Apply).
</details>

The detailed mechanics of how the DmnExporter constructs each XML element are covered in Chapter 6 (DMN XML Construction), and the FEEL expression translation logic is covered in Chapter 7 (FEEL Expression Mapping). This chapter focuses on the exporter's structural role in the plugin system and its relationship to the protocol contract.

!!! tip "Choosing Between Exporters"
    Use the CsvExporter when you need a quick, human-readable dump of rule data or when feeding into tools that consume CSV. Use the DmnExporter when you need interoperability with decision engines (Camunda, Drools, IBM ODM) that implement the DMN standard.

## Key Takeaways

- The **Exporter protocol** defines four members: `name`, `file_extension`, `export(lattice, path)`, and `export_bytes(lattice)`.
- The **export name attribute** is the user-facing identifier for the format (`"csv"`, `"dmn"`).
- The **file extension attribute** is singular (not plural like importers) because each exporter produces exactly one output format.
- The **export method** writes to a file and returns the path; the **export_bytes method** returns raw bytes for in-memory consumption.
- **CsvExporter** converts the Lattice to a Polars DataFrame and writes CSV, producing a flat representation that loses metadata.
- **Polars DataFrame conversion** uses a three-step fallback (direct check, relation API, error) to handle multiple Lattice storage backends.
- **DmnExporter** produces DMN 1.3 XML using lxml, accepting `decision_name` and `table_name` as format-specific options.
- Both exporters share the same `_to_polars` conversion logic, demonstrating code reuse across the exporter implementations.

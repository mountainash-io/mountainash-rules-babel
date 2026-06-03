---
title: "Chapter 4: Importers"
description: "The Importer protocol contract and the CsvImporter implementation covering dimension inference, data type detection, and Polars-based CSV reading."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 4: Importers

## Summary

This chapter covers the Importer protocol contract and its concrete implementation, CsvImporter. You will learn how importers declare their name and supported file extensions, how the import_lattice method constructs a Lattice from file data, and the CSV-specific logic for dimension column inference, data type detection, and Polars-based file reading.

## Concepts Covered

- Importer Protocol
- Import Name Attribute
- File Extensions Attribute
- Import Lattice Method
- CsvImporter Class
- Dimension Column Inference
- Data Type Detection
- Polars CSV Read

## Prerequisites

- Chapter 1: Foundations (CSV Format, Lattice Object)
- Chapter 2: Python Plugin Infrastructure (Runtime Checkable Protocol)
- Chapter 3: Plugin Extension Points (Importer Entry Points)

---

## The Importer's Role

An importer is the entry point of the babel pipeline. It reads an external file format, infers or applies metadata, and produces a Lattice object that the rest of the system can work with. The importer must bridge the gap between a format that carries no semantic metadata (like CSV) and the rich Lattice structure that babel's exporters and validators expect.

## Importer Protocol

The **Importer protocol** defines the contract that all importer plugins must satisfy. It is declared in `mountainash_rules_babel/importers/base.py` as a `@runtime_checkable` protocol with two attributes and one method:

```python
@runtime_checkable
class Importer(Protocol):
    name: str
    file_extensions: list[str]

    def import_lattice(self, path: Path, **options) -> Lattice: ...
```

Any class that provides these three members with compatible types satisfies the protocol, whether or not it inherits from or imports the `Importer` class. The protocol is deliberately minimal --- it defines only what the PluginRegistry and the public API need to interact with an importer.

The `**options` keyword argument on `import_lattice` allows each importer to accept format-specific parameters without changing the protocol definition. The CsvImporter, for example, accepts `dimension_columns` and `aggregate_columns` options that have no meaning for other formats.

## Import Name Attribute

The **name attribute** is a string that identifies the importer within the registry. It must be unique across all registered importers. For the built-in CSV importer, the name is `"csv"`.

The name serves two purposes:

- **Lookup key** --- the PluginRegistry uses the name to retrieve a specific importer when the user passes `--format csv` on the CLI or calls `import_lattice(path, format="csv")` in the Python API.
- **Display identifier** --- the CLI's `formats` command lists importers by name so users can see what is available.

The name is a class attribute on the implementation, not an instance attribute, which means it is shared across all instances and does not need to be set in `__init__`:

```python
class CsvImporter:
    name: str = "csv"
```

## File Extensions Attribute

The **file_extensions attribute** is a list of strings identifying the file extensions that this importer can handle. Each extension includes the leading dot (e.g., `".csv"`). The PluginRegistry uses this attribute in its `get_importer_for_extension()` method to enable format auto-detection when the user does not specify a format explicitly.

```python
class CsvImporter:
    file_extensions: list[str] = [".csv"]
```

An importer may support multiple extensions. A hypothetical Excel importer might declare `[".xlsx", ".xls"]` to handle both modern and legacy Excel formats. The registry iterates over all importers and their extensions to find a match, raising `FormatNotFoundError` if no importer supports the given extension.

| Attribute | Type | Purpose | Example |
|-----------|------|---------|---------|
| `name` | `str` | Registry lookup key | `"csv"` |
| `file_extensions` | `list[str]` | Format auto-detection | `[".csv"]` |

## Import Lattice Method

The **import_lattice method** is the core of any importer. It accepts a file path and optional keyword arguments, reads the file, constructs the appropriate metadata structures, and returns a fully-formed Lattice object.

The method signature from the protocol is:

```python
def import_lattice(self, path: Path, **options) -> Lattice: ...
```

The return type is always `Lattice`, which ensures that all importers produce the same intermediate representation regardless of input format. This uniformity is what allows exporters, validators, and decomposers to work with any imported data without knowing its original format.

The method must handle several responsibilities:

1. **Read the file** from the given path
2. **Determine which columns are dimensions** (inputs) and which are aggregates (outputs)
3. **Detect data types** for each dimension column
4. **Construct metadata** (`DimensionsMetadata` with `Dimension` objects)
5. **Build and return** the Lattice

#### Diagram: Import Lattice Data Flow

<iframe src="../../sims/import-lattice-flow/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>Import Lattice Data Flow</summary>
Type: workflow
**sim-id:** import-lattice-flow<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Trace the data transformation from a raw CSV file through CsvImporter's processing stages to the final Lattice object.

**Components:** Sequential nodes: CSV File, Polars read_csv, DataFrame, Dimension Column Inference, Data Type Detection, Dimension/Metadata Construction, Lattice Assembly. Data annotations on each arrow show what is produced at each stage (e.g., raw bytes to DataFrame, column list to dimension list).

**Interactions:** Click each stage to see the corresponding code snippet from CsvImporter. Hover to see input/output types at that stage. Animated flow shows data moving through the pipeline.

**Colors:** File I/O stages in gold, inference stages in teal, construction stages in dark green, final Lattice in steel blue.

**Learning Objective:** Trace the complete import pipeline from file to Lattice (Bloom: Apply).
</details>

## CsvImporter Class

The **CsvImporter** is babel's built-in implementation of the Importer protocol. It reads CSV files using Polars, infers dimension columns when not explicitly specified, detects data types from the Polars schema, and constructs a Lattice with the appropriate metadata.

The full implementation is compact --- under 50 lines. The constructor requires no arguments because all configuration is passed through the `import_lattice` method's `**options`:

```python
class CsvImporter:
    name: str = "csv"
    file_extensions: list[str] = [".csv"]

    def import_lattice(
        self,
        path: Path,
        *,
        dimension_columns: list[str] | None = None,
        aggregate_columns: dict[str, str] | None = None,
        **options,
    ) -> Lattice:
```

The method accepts two optional parameters beyond the required `path`:

- **dimension_columns** --- an explicit list of column names to treat as input dimensions. When `None`, the importer infers dimensions automatically.
- **aggregate_columns** --- a dictionary mapping column names to aggregation operations (e.g., `{"base_premium": "assign"}`). Columns listed here are treated as outputs.

This design provides flexibility: users who know their data can specify columns explicitly for precision, while users exploring a new dataset can rely on automatic inference.

## Polars CSV Read

The CsvImporter uses the **Polars** library to read CSV files. Polars is a high-performance DataFrame library written in Rust with Python bindings. Babel chose Polars over pandas for several reasons:

- **Speed** --- Polars is significantly faster for large files due to its Rust implementation and lazy evaluation capabilities
- **Type inference** --- Polars infers column types (integers, floats, strings) during parsing, which babel leverages for data type detection
- **Memory efficiency** --- Polars uses Apache Arrow as its in-memory format, which is more compact than pandas' NumPy-based storage

The CSV read is a single line:

```python
df = pl.read_csv(path)
```

This produces a `pl.DataFrame` where each column has an inferred Polars data type (e.g., `pl.Int64`, `pl.Utf8`, `pl.Float64`). The CsvImporter then uses this type information in the data type detection step.

## Dimension Column Inference

When the user does not specify `dimension_columns`, the CsvImporter must **infer** which columns are input dimensions and which are output aggregates. The inference algorithm uses an exclusion-based approach:

```python
if dimension_columns is None:
    non_agg = set((aggregate_columns or {}).keys())
    dimension_columns = [
        c for c in df.columns
        if c not in non_agg and c != "rule_name"
    ]
```

The logic works as follows:

1. Start with all columns in the DataFrame
2. Exclude any columns explicitly listed as aggregates (from `aggregate_columns`)
3. Exclude the special `rule_name` column, which is a metadata column not part of the decision logic
4. Everything remaining is treated as a dimension

This approach is a reasonable default for simple decision tables where most columns are inputs and only one or two are outputs. However, it can misclassify columns in tables where there are multiple unlabeled output columns. In such cases, explicit `dimension_columns` specification is recommended.

The inference algorithm makes a deliberate trade-off: it is simple and predictable at the cost of requiring explicit configuration for complex tables. The alternative --- using heuristics like "the last column is always the output" --- would be fragile and format-dependent.

## Data Type Detection

After identifying dimension columns, the CsvImporter **detects the data type** of each dimension by examining the Polars column schema. The detection maps Polars types to Python types:

```python
dtype = df.schema[col_name]
py_type: type = str
if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
             pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
    py_type = int
elif dtype in (pl.Float32, pl.Float64):
    py_type = float
```

The mapping is intentionally coarse:

| Polars Type(s) | Python Type | Use in Babel |
|---------------|-------------|--------------|
| Int8 through UInt64 | `int` | Numeric comparisons, range expressions |
| Float32, Float64 | `float` | Numeric comparisons, range expressions |
| Everything else | `str` | String matching, exact match, prefix/suffix |

This three-way classification is sufficient because the FEEL expression mapping (Chapter 7) branches on whether a value is numeric or string-typed. Integer and float dimensions produce unquoted FEEL literals (`42`, `3.14`), while string dimensions produce quoted FEEL strings (`"Gold"`).

Each detected dimension is wrapped in a `Dimension` object:

```python
Dimension(
    dimension_name=col_name,
    match_strategy=MatchStrategy.EXACT,
    data_type=py_type,
)
```

Note that the CsvImporter assigns `MatchStrategy.EXACT` to every dimension by default. CSV files carry no information about match strategies; more sophisticated strategies (range, prefix, set membership) must be specified through external metadata or by a higher-level orchestration layer.

#### Diagram: Data Type Detection Pipeline

<iframe src="../../sims/data-type-detection/main.html" width="100%" height="400px" scrolling="no"></iframe>
<details markdown="1">
<summary>Data Type Detection Pipeline</summary>
Type: chart
**sim-id:** data-type-detection<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show how Polars column types flow through the detection logic to produce Python type annotations on Dimension objects.

**Components:** Left column: Polars type nodes (Int8, Int16, ..., UInt64, Float32, Float64, Utf8, Boolean, etc.). Middle: decision diamond nodes for the two if/elif checks. Right column: three Python type nodes (int, float, str). Arrows flow from Polars types through the decision logic to the resulting Python type.

**Interactions:** Click a Polars type to highlight its path through the detection logic. Hover over the Python type nodes to see which FEEL expression patterns use that type.

**Colors:** Polars integer types in dark blue, float types in teal, string/other types in dark green, Python types in crimson.

**Learning Objective:** Apply the data type detection logic to predict the Python type for a given Polars column (Bloom: Apply).
</details>

## Assembling the Lattice

After reading the CSV, inferring dimensions, and detecting types, the CsvImporter assembles all components into a Lattice. The assembly step constructs the `DimensionsMetadata` from the list of `Dimension` objects, builds the `Aggregate` list from any specified aggregate columns, and packages everything with the DataFrame:

```python
metadata = DimensionsMetadata(dimensions=dimensions)

aggregates = []
if aggregate_columns:
    for col_name, operation in aggregate_columns.items():
        aggregates.append(Aggregate(column_name=col_name, operation=operation))

return Lattice(
    dataframe=df,
    metadata=metadata,
    aggregates=aggregates,
    partition_key=None,
)
```

The `partition_key` is always `None` for CSV imports because CSV files do not carry partitioning metadata. The resulting Lattice is ready to be passed to any exporter, validator, or decomposer.

!!! tip "Testing Import Results"
    After importing a CSV, verify the Lattice by checking `lattice.metadata.dimensions` for the expected dimension names and types, and `lattice.count` for the expected number of rows. The CLI's `import` command prints this information automatically.

## Key Takeaways

- The **Importer protocol** defines a minimal three-member contract: `name`, `file_extensions`, and `import_lattice(path, **options)`.
- The **import name attribute** serves as both a registry lookup key and a user-facing identifier.
- The **file extensions attribute** enables format auto-detection when the user omits the `--format` flag.
- The **import_lattice method** bridges the gap between schema-less file formats and the rich Lattice structure.
- **CsvImporter** is the built-in implementation that uses Polars for parsing, exclusion-based dimension inference, and Polars-to-Python type mapping.
- **Dimension column inference** treats all non-aggregate, non-metadata columns as dimensions --- a safe default for simple tables that requires explicit override for complex ones.
- **Data type detection** maps Polars column types to three Python types (`int`, `float`, `str`) that drive downstream FEEL expression generation.
- **Polars CSV read** provides fast, type-aware parsing with a single `pl.read_csv(path)` call.

# Frequently Asked Questions for Mountainash Rules Babel

## Overview and Purpose

### What is mountainash-rules-babel and what problem does it solve?

Mountainash-rules-babel is a format translation engine for decision tables and business rules. It bridges the gap between Python-based rule engines and enterprise decision management platforms by converting between internal Lattice representations and external standards like CSV and OMG DMN 1.3 XML with FEEL expressions.

The core problem it addresses is format interoperability. Decision tables authored in Python using mountainash-rules need to be shared with business analysts, imported into enterprise platforms like Camunda or Trisotech, or validated for correctness before deployment. Without a translation layer, each integration would require custom code. Mountainash-rules-babel provides a plugin-based architecture with four extension axes — exporters, importers, decomposers, and validators — that standardizes these translations and makes the system extensible by third parties.

### What is the relationship between mountainash-rules-babel and mountainash-rules?

Mountainash-rules is the core rule engine package that defines the fundamental data structures — Lattice, Dimension, and MatchStrategy — used to represent decision tables in Python. Mountainash-rules-babel is a companion package that handles format translation for those data structures. It depends on the core package for its domain model.

The Lattice object from mountainash-rules is the central data structure that flows through all babel operations. Importers produce Lattice objects from external formats, exporters consume Lattice objects to generate external formats, validators inspect Lattice objects for quality issues, and decomposers split Lattice objects into smaller fragments. The babel package never modifies the Lattice semantics; it only translates between representations.

### What formats does mountainash-rules-babel support?

Mountainash-rules-babel ships with two built-in format pairs. For import, it supports CSV files via the CsvImporter, which reads tabular data using Polars and infers dimension metadata including column types and match strategies. For export, it supports both CSV via the CsvExporter (using Polars DataFrame conversion) and OMG DMN 1.3 XML via the DmnExporter, which generates standards-compliant XML with FEEL expressions for all 11 MatchStrategy values.

The plugin architecture means additional formats can be added by third parties. Any class conforming to the Importer or Exporter protocol can be registered via entry points and discovered automatically by the PluginRegistry, making it straightforward to add support for formats like JSON, Excel, or proprietary enterprise formats.

### Who is the target audience for this package?

The primary audience is Python developers and rules engineers who work with decision tables across multiple platforms. This includes developers building integrations between Python rule engines and enterprise business rules management systems (BRMS), data engineers who maintain decision tables in CSV format and need to validate or export them, and platform teams who need DMN-compliant representations for compliance or interoperability.

A secondary audience is plugin developers who want to extend the format support by implementing new importers, exporters, validators, or decomposers. The protocol-based plugin architecture and entry point discovery system are designed to make extension straightforward without modifying the core package.

### What is the DMN 1.3 standard and why does mountainash-rules-babel target it?

DMN (Decision Model and Notation) is an OMG (Object Management Group) standard for modeling and exchanging business decisions. Version 1.3 defines an XML interchange format that enables decision tables to be shared between different vendors and platforms. DMN is the industry standard for decision table interoperability, supported by platforms like Camunda, Drools, Trisotech, and IBM ODM.

Mountainash-rules-babel targets DMN 1.3 because it is the most widely supported version of the standard. The DMN XML format includes a well-defined hierarchy: a definitions element wraps one or more decision elements, each containing a decisionTable with input columns, output columns, and rule rows. FEEL (Friendly Enough Expression Language) is the expression language specified by DMN for defining cell-level conditions and outputs in decision tables.

## Plugin Architecture and Registry

### How does the PluginRegistry discover plugins?

The PluginRegistry uses Python's `importlib.metadata` entry point mechanism to discover plugins at runtime. When the registry initializes, it scans four entry point groups: `mountainash_babel.exporters`, `mountainash_babel.importers`, `mountainash_babel.decomposers`, and `mountainash_babel.validators`. Each installed Python package can declare entry points in these groups via its `pyproject.toml` file.

Entry point discovery is automatic — no configuration files or manual registration steps are needed. When a package is installed into the Python environment and declares the appropriate entry point groups, the PluginRegistry finds it on the next scan. This means third-party plugins work identically to built-in ones from the user's perspective. The registry pattern decouples plugin implementation from the core babel package.

### What are the four extension axes in the plugin architecture?

The four extension axes correspond to the four types of operations that mountainash-rules-babel supports. Exporters convert Lattice objects into external format representations (CSV, DMN XML). Importers parse external format files and produce Lattice objects. Validators inspect Lattice objects for quality issues and produce ValidationReport results. Decomposers split complex Lattice objects into smaller Fragment collections with provenance tracking.

Each axis has its own Python protocol definition, its own entry point group for discovery, and its own CLI subcommand. This separation means plugins only need to implement the protocol for their specific concern. An organization might ship a custom exporter without touching import or validation logic, and the PluginRegistry will discover and load only what is installed.

### How do entry point groups work in pyproject.toml?

Entry point groups are declared in a package's `pyproject.toml` under the `[project.entry-points]` section (or equivalent for the build backend). Each group name follows the pattern `mountainash_babel.<axis>` where axis is one of `exporters`, `importers`, `decomposers`, or `validators`. Within each group, individual entries map a plugin name to a dotted Python path pointing to the plugin class.

For example, a custom exporter might declare `my_format = "my_package.exporters:MyFormatExporter"` under `[project.entry-points."mountainash_babel.exporters"]`. When the PluginRegistry scans entry points, it finds this declaration, loads the class, and makes it available by name. The entry point mechanism is part of Python's packaging standard, so it works with pip, uv, and any PEP 517/621-compliant build system.

### How do I register a new plugin with the PluginRegistry?

To register a new plugin, you need to create a class that conforms to one of the four protocols (Exporter, Importer, Validator, or Decomposer) and declare it as an entry point in your package's `pyproject.toml`. The class must implement all required methods and attributes defined by the protocol — for example, an Exporter needs `export_name`, `file_extension`, `export()`, and `export_bytes()`.

Once the class is implemented and the entry point is declared, install the package into the same Python environment as mountainash-rules-babel. The PluginRegistry will automatically discover the plugin on its next initialization. No code changes to the babel package are needed. The Runtime Checkable Protocol decorators on the protocol definitions allow the registry to verify at load time that a discovered class actually conforms to the expected interface.

### What is the difference between the Exporter and Importer protocols?

The Exporter protocol defines a contract for converting Lattice objects into external formats. It requires four members: `export_name` (a string identifier), `file_extension` (the output file suffix), `export()` (which writes to a file path), and `export_bytes()` (which returns the serialized content as bytes). The dual export methods support both file-based workflows and in-memory operations like HTTP responses.

The Importer protocol defines a contract for parsing external files into Lattice objects. It requires three members: `import_name` (a string identifier), `file_extensions` (a collection of recognized file suffixes — note the plural, since a format like CSV might use `.csv` or `.tsv`), and `import_lattice()` which reads a file and returns a fully constructed Lattice object with inferred dimensions and metadata.

## Importing Decision Tables

### How does the CsvImporter work?

The CsvImporter reads CSV files and produces Lattice objects by performing dimension column inference, data type detection, and match strategy assignment. It uses Polars for efficient CSV parsing, which handles large files and provides automatic type inference for numeric, string, and date columns.

The import process has several stages. First, Polars reads the raw CSV data. Then the CsvImporter examines each column to determine whether it represents an input dimension or an output column. Data type detection identifies whether values are numeric, categorical, or pattern-based. Based on the detected types and value patterns, the importer assigns appropriate MatchStrategy values to each dimension. The result is a fully constructed Lattice object that preserves the semantics of the original CSV data.

### What is dimension column inference?

Dimension column inference is the process by which the CsvImporter determines the role and characteristics of each column in a CSV file. Since CSV is an untyped format — everything is a string — the importer must analyze column contents to determine whether each column is an input dimension or an output, what data type it represents, and what match strategy should be applied.

The inference examines value patterns in each column. Columns with numeric ranges might be assigned RANGE or GREATER_THAN strategies. Columns with distinct categorical values get EXACT matching. Columns containing patterns like prefixes or wildcards receive the corresponding strategy. This inference is heuristic-based and works well for well-structured decision tables, though complex or ambiguous columns may need manual metadata overrides after import.

### What is data type detection in the CSV importer?

Data type detection is the step within CSV import where the CsvImporter determines the semantic data type of each column's values. Polars provides initial type inference (integer, float, string, date, etc.), but the CsvImporter adds a layer of semantic analysis on top. A column of strings might contain email addresses, product codes, IP address prefixes, or categorical labels — each implying different match strategies.

The detection influences downstream processing. Numeric columns enable range-based match strategies (RANGE, GREATER_THAN, LESS_THAN). String columns with set-like values suggest SET_MEMBERSHIP or SET_EXCLUSION. Pattern columns with wildcards or partial matches map to PREFIX, SUFFIX, or CONTAINS strategies. Accurate type detection is essential for generating correct FEEL expressions when the Lattice is later exported to DMN.

### How does the import_lattice method construct a Lattice object?

The `import_lattice()` method is the core entry point of the Importer protocol. It accepts a file path and returns a complete Lattice object. For the CsvImporter, this involves reading the CSV with Polars, running dimension column inference and data type detection, constructing Dimension objects for each input column with the appropriate MatchStrategy, and assembling the rows into the Lattice's internal representation.

The method must produce a Lattice that is semantically equivalent to the source data. This means all input conditions, output values, and dimension metadata must be faithfully represented. The constructed Lattice can then be passed to exporters for format conversion, validators for quality checking, or decomposers for fragmentation — all without any knowledge of where the data originally came from.

### Why does mountainash-rules-babel use Polars for CSV operations?

Polars is used for both CSV import (reading) and CSV export (DataFrame conversion) because it provides efficient columnar processing, strong type inference, and consistent handling of missing values. Compared to Python's built-in csv module, Polars handles large files with low memory overhead and automatically detects column types without manual schema definition.

For import, Polars' `read_csv()` function provides the initial data frame that the CsvImporter then analyzes for dimension inference. For export, the CsvExporter converts Lattice data into a Polars DataFrame and uses its `write_csv()` method to produce well-formatted output. Using a single library for both directions ensures consistency in how data types, null values, and encoding are handled during round-trip operations.

## Exporting and DMN Generation

### How does the DmnExporter generate DMN 1.3 XML?

The DmnExporter builds an XML tree following the DMN 1.3 schema hierarchy. It starts with a `definitions` element (the root), then creates a `decision` element containing a `decisionTable` element. Within the decision table, it generates `input` elements for each Lattice dimension, `output` elements for the result columns, and `rule` elements for each row of the decision table.

The XML tree is constructed using Python's XML libraries with security hardening (entity resolution disabled, file size limits enforced). Each input entry within a rule is converted to a FEEL expression based on the dimension's MatchStrategy and the cell's value. The completed XML tree is serialized to bytes or written to a file, producing standards-compliant DMN 1.3 that can be imported by any DMN-compatible platform.

### What are the DMN XML elements and how do they nest?

The DMN 1.3 XML structure follows a strict hierarchy. The `definitions` element is the root and contains namespace declarations and schema metadata. Inside definitions, one or more `decision` elements represent individual decisions. Each decision contains exactly one `decisionTable` element that holds the tabular rule logic.

Within a decisionTable, `input` elements define the input columns (corresponding to Lattice dimensions), each with an `inputExpression` specifying the variable name. `output` elements define the result columns. `rule` elements represent individual rows, each containing `inputEntry` elements (with FEEL expressions defining conditions) and `outputEntry` elements (with result values). This structure maps directly to the Lattice model: dimensions become inputs, result columns become outputs, and rows become rules.

### How does FEEL expression mapping work for the 11 MatchStrategy values?

Each of the 11 MatchStrategy values in mountainash-rules maps to a specific FEEL expression pattern in DMN. The DmnExporter examines the MatchStrategy assigned to each dimension and the cell value for each rule row, then generates the appropriate FEEL expression. This mapping is the most technically complex part of the export process.

EXACT maps to a simple equality test (e.g., `"Active"`). NOT_EQUAL uses negation (`not("Inactive")`). RANGE generates interval notation (`[18..65]`). GREATER_THAN and LESS_THAN produce comparison expressions (`> 100`, `< 50`). PREFIX uses `starts with()`, SUFFIX uses `ends with()`, and CONTAINS uses `contains()`. SET_MEMBERSHIP generates a list test (`"A","B","C"`), and SET_EXCLUSION uses `not("A","B","C")`. REGEX is mapped to a `matches()` function call with the pattern string.

### What is the FEEL Exact Match mapping?

The FEEL Exact Match maps a cell value with MatchStrategy.EXACT to a simple literal value in the FEEL expression. For string values, this produces a quoted string like `"Active"` or `"Premium"`. For numeric values, it produces an unquoted number like `42` or `3.14`. This is the simplest and most common FEEL mapping, used when a rule condition requires an exact equality test against a single value.

In DMN, an inputEntry containing just a literal value is interpreted as an equality test. The DMN platform evaluates the input variable against this value and the rule matches only if they are equal. This maps directly to the semantics of MatchStrategy.EXACT in mountainash-rules, making it a lossless translation with no semantic gap between the Python and DMN representations.

### How does the export handle NA sentinel values?

NA sentinel handling addresses the case where a decision table cell contains a missing or "don't care" value. In mountainash-rules, NA sentinels indicate that a dimension is unconstrained for a particular rule row — any input value should match. The DmnExporter must translate this concept into the DMN equivalent.

In DMN 1.3 FEEL, an empty inputEntry (or one containing just a dash `-`) means "any value matches." The DmnExporter detects NA sentinel values during export and generates the appropriate empty or dash expression. This is critical for correctness because incorrectly exporting an NA sentinel as a literal value would change the rule's semantics from "match anything" to "match only the literal string 'NA'." The sentinel detection works across all data types and MatchStrategy values.

### What is the difference between the export() and export_bytes() methods?

The Exporter protocol requires two output methods to support different consumption patterns. The `export()` method takes a Lattice and a file path, serializes the Lattice to the target format, and writes the result directly to disk. The `export_bytes()` method takes only a Lattice and returns the serialized content as a Python bytes object without writing to disk.

The dual-method design serves practical needs. File-based export is needed for CLI workflows, batch processing, and integration with file-based toolchains. Bytes-based export is needed for HTTP API responses, in-memory pipeline processing, database storage, and testing. Both methods must produce identical output for the same Lattice input — the only difference is the delivery mechanism.

### What XML security measures does the exporter apply?

The XML Security Module protects against common XML-based attacks during both export and import of DMN files. Entity resolution is disabled to prevent XML External Entity (XXE) attacks, where a malicious DMN file could reference external resources or local files. File size limits are enforced to prevent denial-of-service through extremely large XML documents.

These measures are especially important because DMN files may originate from external sources — business analysts, partner organizations, or enterprise platforms — and could be crafted maliciously. The security module applies safe defaults that prevent the most common XML attack vectors while still supporting valid DMN 1.3 documents. The defenses are applied transparently during XML tree construction and parsing, requiring no action from plugin developers.

## Validation and Quality

### What is the validation pipeline and how does it work?

The validation pipeline runs one or more Validator plugins against a Lattice object and produces a ValidationReport summarizing any issues found. Each validator implements the Validator protocol and focuses on a specific aspect of rule table quality. The pipeline collects results from all validators into a unified report with severity-categorized issues.

The four built-in validators check for conflicts (overlapping rules that could produce ambiguous results), coverage (gaps in the input space that no rule addresses), orphans (rules that can never fire because they are shadowed by other rules), and round-trip integrity (whether a Lattice survives export and re-import without semantic changes). The pipeline can be run via the CLI's validate subcommand or programmatically through the Validator protocol.

### What does the ConflictsValidator check?

The ConflictsValidator examines a Lattice for pairs of rules whose input conditions overlap, meaning the same input could match multiple rules and produce ambiguous results. In decision tables, conflicts are a common source of bugs — if two rules both match an input but specify different outputs, the result depends on rule ordering rather than explicit logic.

The validator analyzes each pair of rules across all dimensions to determine if their conditions can simultaneously match. When it finds an overlap, it creates a ValidationIssue with details about which rules conflict, which dimensions are involved, and the overlapping value ranges. These issues are included in the ValidationReport with appropriate severity, allowing developers to prioritize fixes based on the likelihood and impact of ambiguous matches.

### What does the CoverageValidator check?

The CoverageValidator analyzes whether the decision table's rules collectively cover the entire expected input space. A coverage gap means there exist valid input combinations that no rule matches, which could cause runtime errors or unexpected default behavior when the rule engine encounters those inputs.

The validator computes the theoretical input space from the dimension definitions and compares it against the union of all rule conditions. Gaps are reported as ValidationIssue entries describing the uncovered input combinations. Coverage analysis is especially important for tables exported to enterprise platforms where completeness may be a compliance requirement, or where a missing rule would cause a process to fail rather than return a default value.

### What does the OrphansValidator check?

The OrphansValidator identifies rules that can never fire because they are completely shadowed by other rules with higher priority or broader conditions. An orphan rule represents dead logic — it exists in the table but has no effect on any output. Orphans often result from incremental table modifications where new rules are added without removing or adjusting rules they supersede.

The validator checks each rule to determine whether every input combination it could match is already captured by one or more other rules that take precedence. Orphaned rules waste space, create maintenance confusion, and may indicate logical errors in the table design. The ValidationIssue entries identify the orphan rule and the rules that shadow it, making cleanup straightforward.

### What does the RoundTripValidator check?

The RoundTripValidator verifies that a Lattice survives a full export-import cycle without semantic changes. It exports the Lattice to a target format, re-imports the result, and compares the original and round-tripped Lattice objects for equivalence. Any differences indicate that the export or import process is losing or altering information.

Round-trip validation is critical for ensuring translation fidelity. A FEEL expression that does not perfectly capture a MatchStrategy's semantics would produce a different Lattice when re-imported. Similarly, dimension metadata loss during CSV export would produce a less-informed Lattice on re-import. The RoundTripValidator catches these subtle issues that other validators miss because they examine the table's static properties rather than its translation behavior.

### What is the ValidationReport dataclass?

The ValidationReport dataclass is the standardized output structure for all validation operations. It contains a collection of ValidationIssue entries, each with a severity level, a description of the problem, and contextual details like affected rule indices or dimension names. The report provides methods for filtering issues by severity and summarizing overall table quality.

The ValidationReport is shared across all four validator types and the decomposition subsystem (DecompositionResult includes validation data). This standardization means consumers of validation results — whether the CLI, an API endpoint, or a CI/CD pipeline — can process reports uniformly regardless of which validators produced them. The severity categorization (error, warning, info) allows automated tooling to fail builds on errors while passing on warnings.

### How do I run validators from the CLI?

The Typer CLI provides a `validate` subcommand that runs all registered validators against a Lattice from a specified file. The command accepts a file path (CSV or DMN), imports the file to create a Lattice, discovers all installed Validator plugins via the PluginRegistry, runs each validator, and prints a consolidated ValidationReport to the console.

The output shows each ValidationIssue with its severity, description, and context. Exit codes reflect the highest severity found — zero for clean reports, non-zero for errors — making the command suitable for CI/CD integration. Because validators are discovered via entry points, installing a third-party validator package automatically includes it in CLI validation runs without any configuration changes.

## CLI and Practical Usage

### What CLI commands does mountainash-rules-babel provide?

Mountainash-rules-babel provides a Typer-based CLI with four main subcommands. The `export` command converts a Lattice from one format to another (e.g., CSV to DMN). The `import` command reads an external file and produces a Lattice (useful for inspection and pipeline workflows). The `validate` command runs all registered validators and reports quality issues. The `decompose` command splits a complex table into normalized fragments.

Each subcommand integrates with the PluginRegistry to discover available format plugins. The export command lists available exporters if no format is specified. The import command selects an importer based on the input file's extension. All commands support standard options for output paths, format selection, and verbosity. The CLI is the primary interface for batch processing and CI/CD integration.

### How do I export a decision table to DMN 1.3 XML?

To export a decision table to DMN 1.3 XML, use the CLI export command specifying the input file, the output format, and the destination path. The command imports the source file to create a Lattice, selects the DmnExporter plugin, and generates the DMN XML output. The resulting file conforms to the DMN 1.3 schema and includes FEEL expressions for all input conditions.

Programmatically, you can instantiate the DmnExporter directly and call its `export()` or `export_bytes()` method with a Lattice object. The exporter handles the full XML tree construction, FEEL expression mapping for all 11 MatchStrategy values, NA sentinel conversion, and XML security hardening. The output can be directly imported into DMN-compatible platforms like Camunda, Drools, or Trisotech for execution or further editing.

### How do I import a CSV file into a Lattice?

To import a CSV file, use the CLI import command with the path to the CSV file. The command selects the CsvImporter based on the file extension, reads the file using Polars, performs dimension column inference and data type detection, and constructs a Lattice object. The imported Lattice can then be piped to export or validate commands.

Programmatically, instantiate the CsvImporter and call `import_lattice()` with the file path. The method returns a fully constructed Lattice with dimensions, match strategies, and row data. Review the inferred dimension metadata to verify the importer's heuristic choices. For tables with complex or ambiguous column patterns, you may need to adjust the inferred MatchStrategy assignments after import before exporting to DMN.

### What happens when a requested format is not found?

When a CLI command specifies a format that has no registered plugin, the PluginRegistry raises a FormatNotFoundError. This error is part of the BabelError exception hierarchy and includes a descriptive message listing the requested format name and the available registered formats. The CLI catches this error and presents a user-friendly message suggesting the available alternatives.

FormatNotFoundError can occur in several scenarios: the format name is misspelled, the plugin package is not installed in the current environment, or the entry point declaration is incorrect. The error message guides the user toward resolution by showing what plugins are actually available, which often reveals that a package installation is missing or that the format name does not match the plugin's registered name.

### What is the BabelError exception hierarchy?

The BabelError exception hierarchy provides structured error handling across all babel operations. BabelError is the base exception class from which all babel-specific errors derive. FormatNotFoundError signals that a requested export or import format has no registered plugin. ValidationError wraps validation failures when used programmatically (as opposed to the CLI, which prints reports).

The hierarchy allows consumers to catch errors at the appropriate level of granularity. Catching BabelError handles all babel-related failures. Catching FormatNotFoundError specifically handles missing plugin scenarios. Catching ValidationError specifically handles rule table quality failures. This pattern follows Python exception hierarchy conventions and integrates cleanly with try/except blocks in pipeline code and with CLI error formatting in the Typer application.

## Decomposition and Advanced Topics

### What is table decomposition and when should I use it?

Table decomposition is the process of splitting a large, complex decision table into smaller, normalized fragments. Each fragment contains a subset of the original table's dimensions and rules, making it easier to understand, maintain, and validate independently. The Decomposer protocol and DecompositionResult dataclass define the interface and output structure.

Decomposition is useful when a monolithic decision table has grown too large for effective review, when different dimension groups are maintained by different teams, when you need to identify logically independent rule subsets, or when an enterprise platform imposes size limits on imported decision tables. The decomposition preserves row provenance — each fragment tracks which original rows it contains — so the fragments can be traced back to the source table.

### What is a Fragment dataclass?

The Fragment dataclass represents a single piece of a decomposed decision table. It contains a subset of the original Lattice's dimensions and the corresponding rows that involve those dimensions. Each Fragment is a self-contained rule table that can be independently exported, validated, or analyzed.

A Fragment includes metadata about its dimension group (which dimensions are included), the row indices from the original table, and the extracted row data. This provenance tracking is essential for maintaining traceability — when a validator reports an issue in a fragment, the row indices map back to the original monolithic table. The Fragment dataclass is the basic unit of the DecompositionResult, which collects all fragments and includes overall decomposition metadata.

### What is DecompositionResult and what does it contain?

DecompositionResult is a dataclass that captures the complete output of a decomposition operation. It contains the collection of Fragment objects produced by the decomposer, metadata about the dimension groupings used, and optionally a ValidationReport summarizing any issues detected during decomposition (such as rows that could not be cleanly assigned to a single fragment).

The inclusion of ValidationReport in DecompositionResult connects the decomposition and validation subsystems. A decomposer might detect that certain rows span dimension groups in ways that prevent clean fragmentation — these situations are reported as validation issues within the decomposition result. This design means consumers can inspect both the fragments and any decomposition warnings in a single result object.

### How do Python protocols enable the plugin system?

Mountainash-rules-babel uses Python protocols (from `typing`) decorated with `@runtime_checkable` to define the contracts for each plugin type. A protocol specifies the methods and attributes a class must have without requiring inheritance from a base class. This is structural subtyping — a class conforms to a protocol if it has the right methods, regardless of its class hierarchy.

The `@runtime_checkable` decorator enables `isinstance()` checks at runtime, which the PluginRegistry uses to verify that discovered entry points actually conform to the expected protocol before registering them. This catches misconfigured plugins early — if a class is declared as an exporter entry point but is missing the `export_bytes()` method, the registry can detect and report the problem rather than failing later when the method is called.

### How do I implement a custom Exporter plugin?

To implement a custom Exporter, create a class that satisfies the Exporter protocol. The class needs four members: an `export_name` string attribute identifying the format, a `file_extension` string attribute for the output file suffix, an `export(lattice, path)` method that writes the Lattice to a file, and an `export_bytes(lattice)` method that returns the serialized Lattice as bytes.

Declare the class as an entry point under `mountainash_babel.exporters` in your package's `pyproject.toml`. For example: `my_format = "my_package:MyExporter"` under `[project.entry-points."mountainash_babel.exporters"]`. Install the package, and the PluginRegistry will discover the exporter automatically. The Typer CLI will list it as an available export format, and the `export` subcommand will be able to select it by name.

### How do I implement a custom Validator plugin?

To implement a custom Validator, create a class conforming to the Validator protocol. The class must implement a validation method that accepts a Lattice and returns a ValidationReport containing any ValidationIssue entries it detected. Each issue should include a severity level, a human-readable description, and contextual information like affected rule indices.

Register the validator via the `mountainash_babel.validators` entry point group in `pyproject.toml`. Once installed, the validator runs automatically as part of the CLI's validate subcommand and is included in any programmatic validation pipeline that queries the PluginRegistry for installed validators. Custom validators can check domain-specific rules that the built-in validators do not cover — for example, verifying that output values conform to a specific enumeration or that dimension ranges align with external data sources.

### What is the FEEL REGEX match mapping?

The REGEX MatchStrategy maps to FEEL's `matches()` function, which applies a regular expression pattern to the input value. The DmnExporter generates an expression like `matches(?, "^[A-Z]{2}\\d{4}$")` where the pattern string comes from the cell value in the decision table. This enables complex pattern-based matching in DMN that goes beyond simple string operations.

REGEX is the most powerful but also the most platform-dependent of the 11 MatchStrategy mappings. While DMN 1.3 specifies `matches()` as a standard FEEL function, different DMN platforms may support different regex dialects or impose pattern restrictions. When exporting tables with REGEX strategies, verify that the target platform supports the specific regex patterns used. The other ten MatchStrategy mappings are more portable across platforms.

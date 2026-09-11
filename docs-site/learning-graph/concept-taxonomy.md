# Concept Taxonomy

This taxonomy organizes the 70 mountainash-rules-babel concepts into 8 categories.

## Categories

### FOUND — Foundation Concepts
Prerequisites: decision tables, business rules, CSV/XML formats, DMN standard, FEEL language, Python protocols, entry points, Lattice.

### PLUG — Plugin Architecture
PluginRegistry with auto-discovery via importlib.metadata entry points across four extension axes.

### IMP — Importers
Importer protocol and CsvImporter with dimension inference, data type detection, and Polars CSV reading.

### EXP — Exporters
Exporter protocol, CsvExporter, and DmnExporter with full DMN 1.3 XML construction and FEEL expression mapping for 11 MatchStrategies.

### VALID — Validators
Validator protocol, ValidationIssue/ValidationReport dataclasses, and four built-in validators (conflicts, coverage, orphans, round-trip).

### DECOMP — Decomposers
Decomposer protocol with Fragment and DecompositionResult dataclasses for table normalization.

### CLI — CLI Interface
Typer-based command-line interface with export, import, validate, and formats subcommands.

### ERROR — Error Handling
BabelError exception hierarchy with format-specific and validation-aware error types.

## Taxonomy Summary Table

| TaxonomyID | Category Name | Concept Range | Count |
|------------|---------------|---------------|-------|
| FOUND | Foundation Concepts | 1-10 | 10 |
| PLUG | Plugin Architecture | 11-17 | 7 |
| IMP | Importers | 18-25 | 8 |
| EXP | Exporters | 26-53 | 28 |
| VALID | Validators | 54-60 | 7 |
| DECOMP | Decomposers | 61-63 | 3 |
| CLI | CLI Interface | 64-67 | 4 |
| ERROR | Error Handling | 68-70 | 3 |

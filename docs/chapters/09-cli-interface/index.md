---
title: "Chapter 9: CLI Interface"
description: "The Typer-based command-line interface with export, import, and validate commands that orchestrate the full babel pipeline."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 9: CLI Interface

## Summary

This chapter covers the Typer-based command-line interface that provides user-facing access to all babel operations. You will learn how the Typer CLI App is structured and how the export, import, and validate commands orchestrate the plugin registry, importers, exporters, and validators to perform end-to-end format translation from the terminal.

## Concepts Covered

- Typer CLI App
- Babel Export Command
- Babel Import Command
- Babel Validate Command

## Prerequisites

- Chapter 2: Python Plugin Infrastructure (PluginRegistry Class)
- Chapter 4: Importers (CsvImporter Class)
- Chapter 5: Exporter Architecture (Export Method)
- Chapter 8: Validators and Decomposers (ValidationReport Dataclass, ConflictsValidator, CoverageValidator, OrphansValidator, RoundTripValidator)

---

## Why a CLI?

While babel provides a Python API for programmatic use, many users interact with decision tables through shell scripts, CI/CD pipelines, and manual workflows. A command-line interface provides these users with direct access to babel's import, export, and validation capabilities without writing Python code. The CLI is also the simplest way to explore babel's features and test translations during development.

## Typer CLI App

**Typer** is a Python library for building command-line interfaces with type hints. Babel uses Typer because it generates help text, argument validation, and tab completion from standard Python type annotations, reducing boilerplate compared to argparse or click.

The CLI is defined in `mountainash_rules_babel/cli/main.py`. The entry point is a Typer application object:

```python
import typer
from mountainash_rules_babel.registry import registry

app = typer.Typer(
    name="babel",
    help="Mountain Ash Rules Babel -- translate decision logic between formats."
)
```

The `app` object serves as the command group. Individual commands are registered as decorated functions using `@app.command()`. The CLI is exposed as a console script via the `pyproject.toml` entry:

```toml
[project.scripts]
babel = "mountainash_rules_babel.cli.main:app"
```

This means after installing the package, users can run `babel` directly from the terminal. Typer automatically provides:

- `babel --help` --- shows all available commands with descriptions
- `babel <command> --help` --- shows detailed help for a specific command
- Argument validation with type-appropriate error messages
- Colored output and formatted help text

In addition to the three core commands (export, import, validate), the CLI includes a `formats` command that lists all registered plugins:

```python
@app.command()
def formats() -> None:
    """List available import/export formats."""
    exporters = registry.list_exporters()
    importers = registry.list_importers()
    # ... print formatted lists
```

This command queries the PluginRegistry singleton to discover what formats are currently available, providing users with a quick way to check their installation.

#### Diagram: CLI Command Architecture

<iframe src="../../sims/cli-command-architecture/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>CLI Command Architecture</summary>
Type: diagram
**sim-id:** cli-command-architecture<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show how the Typer app object connects CLI commands to the babel Python API and ultimately to the PluginRegistry.

**Components:** Top row: terminal/shell node. Second row: Typer app node with four command branches (formats, export, import, validate). Third row: babel public API functions (export_lattice, import_lattice, validate). Bottom row: PluginRegistry with its four dictionaries. Arrows show the call chain from user command to registry lookup.

**Interactions:** Click any command to see its full argument list and help text. Hover over API functions to see their signatures. Click the PluginRegistry to see which plugins each command accesses.

**Colors:** Terminal in dark gray, Typer commands in medium purple, API functions in steel blue, registry in dark slate blue.

**Learning Objective:** Trace the execution path from a CLI command to the underlying plugin operations (Bloom: Apply).
</details>

## Babel Export Command

The **export command** is the primary operation for converting decision tables between formats. It reads an input file, imports it into a Lattice, and exports that Lattice to the specified output format.

```python
@app.command(name="export")
def export_cmd(
    format: str = typer.Option(..., "--format", "-f",
                                help="Output format name"),
    input: Path = typer.Option(..., "--input", "-i",
                               help="Input CSV file"),
    output: Path = typer.Option(..., "--output", "-o",
                                help="Output file path"),
    dim: list[str] = typer.Option([], "--dim", "-d",
                                   help="Dimension column names"),
) -> None:
    """Export a Lattice to an external format."""
    lattice = babel.import_lattice(
        input,
        format="csv",
        dimension_columns=dim if dim else None,
    )
    babel.export_lattice(lattice, format, path=output)
    typer.echo(f"Exported {lattice.count} rows to {output} ({format})")
```

The command accepts four options:

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--format` | `-f` | Yes | Output format name (e.g., `dmn`, `csv`) |
| `--input` | `-i` | Yes | Path to the input CSV file |
| `--output` | `-o` | Yes | Path for the output file |
| `--dim` | `-d` | No | Dimension column names (repeatable) |

The `--dim` option can be specified multiple times to list dimension columns explicitly. If omitted, the CsvImporter's dimension inference logic (Chapter 4) determines which columns are dimensions.

A typical export invocation looks like:

```bash
babel export --format dmn --input rules.csv --output rules.dmn
```

Or with explicit dimensions:

```bash
babel export -f dmn -i rules.csv -o rules.dmn -d age_range -d risk_category
```

The export command always uses the CSV importer for the input side (the `format="csv"` is hard-coded). This is a deliberate simplification: the most common workflow is CSV-to-DMN translation. Future versions may add a `--input-format` option to support other input formats.

## Babel Import Command

The **import command** reads a file, constructs a Lattice, and prints summary statistics. It is primarily a diagnostic tool for inspecting input files before export.

```python
@app.command(name="import")
def import_cmd(
    input: Path = typer.Option(..., "--input", "-i",
                               help="Input file path"),
    format: Optional[str] = typer.Option(None, "--format", "-f",
                                          help="Input format (inferred if omitted)"),
    dim: list[str] = typer.Option([], "--dim", "-d",
                                   help="Dimension column names"),
) -> None:
    """Import an external format and show stats."""
    lattice = babel.import_lattice(
        input,
        format=format,
        dimension_columns=dim if dim else None,
    )
    typer.echo(f"Imported {lattice.count} rows")
    typer.echo(f"Dimensions: {[d.dimension_name for d in lattice.metadata.dimensions]}")
    typer.echo(f"Aggregates: {[a.column_name for a in lattice.aggregates]}")
```

Unlike the export command, the import command's `--format` option is optional. When omitted, babel infers the format from the file extension using `registry.get_importer_for_extension()`. This makes the common case simple:

```bash
babel import --input rules.csv
```

The output shows three pieces of information:

1. **Row count** --- how many rules were imported
2. **Dimension names** --- which columns were identified as input dimensions
3. **Aggregate names** --- which columns were identified as outputs

This diagnostic output helps users verify that dimension inference worked correctly before proceeding to export. If the wrong columns were detected as dimensions, the user can re-run with explicit `--dim` flags.

#### Diagram: CLI Workflow Patterns

<iframe src="../../sims/cli-workflow-patterns/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>CLI Workflow Patterns</summary>
Type: workflow
**sim-id:** cli-workflow-patterns<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show the three common CLI workflows: import-only (diagnostic), import-then-export (translation), and import-validate-export (production pipeline).

**Components:** Three horizontal swim lanes. Lane 1: "Diagnostic" with import command only, outputting stats. Lane 2: "Translation" with import implied inside export command, producing output file. Lane 3: "Production" with import, validate, then export commands in sequence, with decision diamond at validate step (pass/fail).

**Interactions:** Click each workflow lane to see the exact shell commands. Hover over nodes to see the babel Python API calls they map to. Click the decision diamond in the production lane to see example pass/fail output.

**Colors:** Diagnostic lane in teal, translation lane in dark green, production lane in crimson (for the validation gate). Command nodes in medium purple, output nodes in steel blue.

**Learning Objective:** Evaluate which CLI workflow pattern is appropriate for different use cases (Bloom: Evaluate).
</details>

## Babel Validate Command

The **validate command** runs one or more validation checks on an imported Lattice and reports the results. It combines the import step with validation in a single command.

```python
@app.command(name="validate")
def validate_cmd(
    input: Path = typer.Option(..., "--input", "-i",
                               help="Input file path"),
    checks: Optional[str] = typer.Option(None, "--checks", "-c",
                                          help="Comma-separated validator names"),
    dim: list[str] = typer.Option([], "--dim", "-d",
                                   help="Dimension column names"),
) -> None:
    """Run validation checks on a Lattice."""
    lattice = babel.import_lattice(
        input,
        format="csv",
        dimension_columns=dim if dim else None,
    )
    check_list = checks.split(",") if checks else None
    report = babel.validate(lattice, checks=check_list)
    typer.echo(f"Valid: {report.is_valid}")
    for issue in report.issues:
        typer.echo(f"  [{issue.severity}] {issue.category}: {issue.message}")
```

The command accepts three options:

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--input` | `-i` | Yes | Path to the input file |
| `--checks` | `-c` | No | Comma-separated list of validator names |
| `--dim` | `-d` | No | Dimension column names (repeatable) |

When `--checks` is omitted, all registered validators run. When specified, only the named validators execute. This allows targeted validation:

```bash
# Run all validators
babel validate --input rules.csv

# Run only the conflicts and coverage checks
babel validate --input rules.csv --checks conflicts,coverage
```

The output format is designed for both human reading and script parsing. The first line shows the overall validity, followed by indented issue lines with severity, category, and message:

```
Valid: False
  [warning] not_implemented: conflicts validator is not yet implemented
  [warning] not_implemented: coverage validator is not yet implemented
  [warning] not_implemented: orphans validator is not yet implemented
  [warning] not_implemented: round_trip validator is not yet implemented
```

The validate command is the natural complement to the export command. A production workflow typically validates first, then exports only if validation passes. Shell scripting makes this straightforward:

```bash
if babel validate --input rules.csv; then
    babel export --format dmn --input rules.csv --output rules.dmn
    echo "Export succeeded"
else
    echo "Validation failed, check issues above"
    exit 1
fi
```

!!! tip "Integrating Validation in CI/CD"
    The validate command's exit code reflects the validation result: zero for valid, non-zero for invalid. This makes it suitable for use in CI/CD pipelines where decision table quality gates are needed before deployment.

## Command Interaction with the Plugin System

All three core commands (export, import, validate) interact with the PluginRegistry through the babel public API (`babel.import_lattice`, `babel.export_lattice`, `babel.validate`). They do not access the registry directly except for the `formats` command. This layering means:

- The CLI commands are thin wrappers around the Python API
- Any behavior available through the CLI is also available programmatically
- The CLI inherits the same error handling (FormatNotFoundError, ValidationError) as the API
- Plugin discovery happens once at module import time, not per-command

The following table summarizes how each command maps to the underlying API:

| CLI Command | API Function(s) | Registry Interaction |
|-------------|-----------------|---------------------|
| `babel formats` | `registry.list_*()` | Direct query |
| `babel export` | `import_lattice()` + `export_lattice()` | Importer + Exporter lookup |
| `babel import` | `import_lattice()` | Importer lookup |
| `babel validate` | `import_lattice()` + `validate()` | Importer + Validator lookup |

#### Diagram: End-to-End Translation Pipeline

<iframe src="../../sims/end-to-end-pipeline/main.html" width="100%" height="500px" scrolling="no"></iframe>
<details markdown="1">
<summary>End-to-End Translation Pipeline</summary>
Type: workflow
**sim-id:** end-to-end-pipeline<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show the complete end-to-end pipeline from a user typing a babel command through CLI parsing, API calls, plugin dispatch, and output generation.

**Components:** Linear flow: User terminal, Typer argument parsing, babel API function call, PluginRegistry lookup, Plugin execution (importer/exporter/validator), Result (file/bytes/report), CLI output formatting, Terminal output. Each node annotated with the module and function name.

**Interactions:** Click any node to see the actual code that executes at that stage. Hover for timing and data type annotations. Dropdown selector to choose which command (export/import/validate) to trace. Animated flow shows data moving through the pipeline.

**Colors:** User interaction nodes in dark gray, CLI layer in medium purple, API layer in steel blue, plugin layer in dark green (importer), crimson (exporter), or gold (validator), output in teal.

**Learning Objective:** Trace the complete execution path of a babel CLI command from terminal to output (Bloom: Analyze).
</details>

## Key Takeaways

- The **Typer CLI App** provides a `babel` command with four subcommands: `formats`, `export`, `import`, and `validate`.
- The **export command** imports a CSV file, translates it to the specified output format, and writes the result to disk, with optional explicit dimension specification via `--dim`.
- The **import command** reads a file into a Lattice and prints diagnostic statistics (row count, dimensions, aggregates), useful for verifying dimension inference before export.
- The **validate command** runs selected or all validators against an imported Lattice, reporting issues with severity, category, and message for each finding.
- All commands use the babel Python API as their execution layer, ensuring that CLI and programmatic usage produce identical results.
- The CLI's exit codes and output format are designed for integration into shell scripts and CI/CD pipelines.

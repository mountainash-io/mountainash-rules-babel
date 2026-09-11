# mountainash-rules-babel

**The format bridge for decision management -- translate rule definitions
between formats, export as standards-compliant DMN, and connect Python rule
engines with the enterprise decision management world.**

## Vision

Business rules cross boundaries. They are authored by analysts in spreadsheets,
evaluated by Python engines in data pipelines, reviewed by auditors in
standards-compliant formats, and consumed by Java-based systems in production.
These boundaries create friction: manual format translation, semantic drift
between representations, and governance gaps where rule definitions exist in one
format but compliance review requires another.

mountainash-rules-babel is the bridge. Import rule tables from CSV, export them
as OMG DMN 1.3 with auto-generated FEEL expressions, and extend to any format
through a plugin architecture. The rule definitions -- dimensions, match
strategies, aggregates -- travel between formats without manual mapping. The
lattice structure preserves all rule semantics across the translation, so a rule
set exported as DMN carries exactly the same logic as the Python-native
evaluation.

A command-line interface fits into any build pipeline, making rule governance
part of the development workflow rather than a manual handoff. Export rules as
DMN on every commit, validate rule tables before deployment, decompose complex
rule sets for review. The same source of truth serves every audience in the
format they need.

## Installation

```bash
pip install mountainash-rules-babel
```

mountainash-rules-babel depends on mountainash-rules for all domain types
including Lattice, Dimension, and MatchStrategy.

## Use Cases

### The Regulatory Rule Handoff

A pricing team defines rules in Python with mountainash-rules. Regulatory review
requires DMN -- the decision table format that regulated industries already know
how to read. mountainash-rules-babel exports the same rule set as DMN 1.3 with
auto-generated FEEL expressions that faithfully represent all eleven match
strategies. The auditor reviews a standards-compliant document. The Python
evaluation and the DMN export come from the same source of truth, eliminating
the translation errors that plague manual format conversion.

### The Cross-Platform Rule Library

An organisation uses Python for analytics and Java for transaction processing.
Business rules need to run in both environments. The rules are authored in
mountainash-rules, evaluated in Python pipelines, and exported as DMN for the
Java-based decision engine. One rule definition, two execution environments,
standards-compliant interchange. Changes to the rules propagate to both
platforms through the same export pipeline.

### The Feature Flag Governance Pipeline

Feature flags grow complex -- percentage rollouts interacting with plan
restrictions, regional overrides, beta populations. The rules live as tabular
data in mountainash-rules. mountainash-rules-babel exports to the appropriate
format for the feature flag service. The CI pipeline validates rule consistency
on every commit and exports the latest definitions automatically, catching
structural issues before they reach production.

## Key Capabilities

### Import and Export Workflow

The primary workflow centres on two operations: importing a rule table from an
external format into a Lattice, and exporting a Lattice to a target format.
Format selection happens automatically by file extension, or you can specify a
format explicitly. This two-step design keeps the workflow simple while
supporting arbitrarily complex format translations underneath.

### DMN Export with FEEL Expression Generation

The DMN exporter produces OMG DMN 1.3 compliant XML with auto-generated FEEL
expressions for all eleven match strategies supported by mountainash-rules. Each
rule cell is translated into a semantically correct, executable FEEL expression
that faithfully represents the original match logic. Customise the output with
decision and table names to match your BPM platform's naming conventions.

### Format Registry and Plugin Discovery

The registry tracks all available importers, exporters, decomposers, and
validators. Discover what formats are available in your installation
programmatically, and build adaptive tooling that responds to the formats
present. Third-party packages can register new formats by declaring entry
points, and the registry picks them up automatically at import time.

### Validation Pipeline

Validators check decision tables for structural issues such as conflicts,
coverage gaps, and orphaned rules. The validation API aggregates findings across
multiple validators and reports them with clear categories and descriptions,
making it straightforward to integrate structural quality checks into your
deployment pipeline.

### Command-Line Interface

The CLI supports import, export, and validation operations, making it
straightforward to integrate decision table management into shell scripts,
Makefiles, and CI/CD pipelines. Rule governance becomes an automated step in
your build process rather than a manual checkpoint.

## Architecture

mountainash-rules-babel uses a protocol-based plugin architecture with four
extension axes: Exporter, Importer, Decomposer, and Validator. Each axis is
defined by a runtime-checkable Protocol, enabling structural subtyping where any
class that implements the required methods is a valid plugin without requiring
inheritance. Plugins are discovered at runtime via importlib.metadata entry
points and stored in a module-level singleton registry.

All format conversions route through Polars DataFrames as the intermediate
representation. Exporters extract the combinations DataFrame from a Lattice,
transform it into the target format's structure, and serialise. Importers parse
the source format into a DataFrame, then construct a Lattice. This consistent
data flow, combined with the protocol contracts, makes it straightforward to add
new formats: implement a protocol, register an entry point, and the ecosystem
expands without modifying the core.

## Contributing

Contributions welcome. The plugin architecture is designed so that new formats
can be added independently: implement the Exporter, Importer, Decomposer, or
Validator protocol, register an entry point in your package's pyproject.toml,
and the registry will discover it automatically.

## Maintaining

The plugin registry and its lifecycle are the primary maintenance surface.
Plugins are discovered via importlib.metadata entry points, and load failures
are handled silently at DEBUG level. When troubleshooting missing formats, check
entry point registration in pyproject.toml and verify that the implementing
class satisfies the runtime-checkable Protocol.

The DMN FEEL expression generator maps all eleven MatchStrategy variants to FEEL
expressions. When new match strategies are added to mountainash-rules, the FEEL
mapping must be extended in the DMN exporter to maintain complete export
coverage. This is the most common cross-package maintenance task.

The package depends on mountainash-rules for all domain types. The test
environment additionally requires mountainash-data, mountainash, and
mountainash-settings. Keep these dependencies aligned when updating across the
mountainash ecosystem, and check the backlog document for known issues before
starting maintenance work.


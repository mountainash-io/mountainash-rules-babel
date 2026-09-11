---
title: 'Mountainash Rules Babel'
description: 'An intelligent textbook for mountainash-rules-babel — a format translation engine for decision tables and DMN'
---


[← Back to Ecosystem](https://docs.mountainash.io/)
# Mountainash Rules Babel

An intelligent textbook for mountainash-rules-babel — a format translation engine for decision tables and DMN

## Getting Started

This is an intelligent textbook built with MkDocs Material. Use the navigation
sidebar on the left to explore chapters, the learning graph, MicroSims, and
supporting reference content.

## Front Matter

- **About** — audience, prerequisites, and how to read the book
- **Course Description** — the seed document used to generate the learning graph

## Chapters

The main body of the book lives under [Chapters](chapters/index.md). Each
chapter has its own folder with a two-digit prefix (e.g. `01-introduction`).


# Mountainash Rules Babel Package Description

## Title

Mountainash Rules Babel: Format Translation Engine for Decision Tables and Business Rules

## Target Audience

Python developers and rules engineers who need to translate decision tables between formats — importing from CSV, exporting to OMG DMN 1.3 XML with FEEL expressions, validating rule table integrity, and decomposing complex tables into normalized fragments.

## Prerequisites

- Intermediate Python (protocols, dataclasses, entry points)
- Basic understanding of decision tables and business rules
- Familiarity with XML and CSV formats
- Understanding of the mountainash-rules core package (Lattice, Dimension, MatchStrategy)

## Topics Covered

1. **Plugin Architecture** — Registry-based plugin system with four extension axes (exporters, importers, decomposers, validators) discovered via `importlib.metadata` entry points
2. **DMN 1.3 Standard** — OMG Decision Model and Notation XML format for interchangeable decision tables
3. **FEEL Expression Mapping** — Translation of 11 MatchStrategy values (EXACT, NOT_EQUAL, RANGE, GREATER_THAN, LESS_THAN, PREFIX, SUFFIX, CONTAINS, SET_MEMBERSHIP, SET_EXCLUSION, REGEX) to DMN FEEL expressions
4. **CSV Round-Trip** — Import CSV files into Lattice objects with dimension inference, and export Lattices back to CSV via Polars
5. **Entry Point Discovery** — Automatic plugin discovery through `mountainash_babel.*` entry point groups in pyproject.toml
6. **Validation Pipeline** — Four validators (conflicts, coverage, orphans, round-trip) producing typed ValidationReport with severity-categorized issues
7. **Decomposition** — Fragment-based table decomposition with DecompositionResult tracking dimension groups and row provenance
8. **CLI** — Typer-based command-line interface with export, import, validate, and decompose subcommands
9. **Error Handling** — BabelError exception hierarchy with format-specific and validation-aware error types
10. **XML Security** — Safe XML parsing with entity resolution disabled and file size limits

## Topics Excluded

- Decision table design methodology and best practices
- DMN execution engines and FEEL evaluation
- Database storage of decision tables
- Rule versioning and governance workflows
- Performance optimization of large rule sets

## Learning Outcomes

After studying this package, developers will be able to:

### Remember

- List the four plugin extension axes (exporters, importers, decomposers, validators)
- Name the four entry point groups used for plugin discovery
- Identify the 11 MatchStrategy values mapped to FEEL expressions

### Understand

- Explain how the PluginRegistry discovers and loads plugins via entry points
- Describe the DMN 1.3 XML structure (definitions, decision, decisionTable, input, output, rule)
- Explain the FEEL expression mapping for each MatchStrategy

### Apply

- Import a CSV file into a Lattice with dimension inference
- Export a Lattice to DMN 1.3 XML with correct FEEL expressions
- Run validators against a Lattice and interpret the ValidationReport

### Analyze

- Compare the Exporter, Importer, Validator, and Decomposer protocol contracts
- Analyze how dimension metadata drives FEEL expression generation

### Evaluate

- Assess ValidationReport results to determine rule table quality
- Evaluate when to use decomposition versus monolithic table export

### Create

- Implement a new Exporter plugin conforming to the Exporter protocol
- Build custom validators and register them via entry points
- Design new MatchStrategy-to-FEEL mappings for domain-specific needs

## Context

Mountainash-rules-babel is the format translation layer for the mountainash rules engine. It converts between internal Lattice representations and external formats (CSV, DMN 1.3 XML) through a plugin-based architecture. The PluginRegistry discovers exporters, importers, decomposers, and validators via `importlib.metadata` entry points, enabling third-party extensions. The DMN exporter maps all 11 MatchStrategy values to standards-compliant FEEL expressions. Four built-in validators check rule table integrity. A Typer CLI provides command-line access to all operations.

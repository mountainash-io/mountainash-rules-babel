---
title: 'Course Description'
description: 'Course description for the Mountainash Rules Babel intelligent textbook: audience, prerequisites, syllabus, and learning outcomes'
---

# Course Description

**Mountainash Rules Babel: Format Translation Engine for Decision Tables and Business Rules**

This is the seed document used to generate this book's [learning graph](learning-graph/index.md) — the source-of-truth description of who this course is for, what it covers, and what a learner should be able to do after studying it. See [index.md](index.md) for the general orientation to the site and [Chapters](chapters/index.md) for the full text.

## Audience

This course is written for Python developers and rules engineers who need to translate decision tables between formats: importing from CSV, exporting to OMG DMN 1.3 XML with FEEL expressions, validating rule table integrity, and decomposing complex tables into normalized fragments. It assumes readers already work with, or are about to work with, decision logic that has to move between systems — a compliance spreadsheet feeding a DMN-based decision engine, for example — rather than readers encountering decision tables for the first time.

## Prerequisites

- Intermediate Python: protocols, dataclasses, and entry points
- A basic understanding of decision tables and business rules
- Familiarity with XML and CSV formats
- Understanding of the mountainash-rules core package (`Lattice`, `Dimension`, `MatchStrategy`), since mountainash-rules-babel translates the `Lattice` objects that package produces

## Syllabus

The course is organized into nine chapters, listed in full at [Chapters](chapters/index.md):

1. **Foundations** — decision tables, business rules, data formats, and the DMN standard
2. **Python Plugin Infrastructure** — protocols, entry points, and the `PluginRegistry`
3. **Plugin Extension Points** — entry point groups for each plugin axis and the `BabelError` hierarchy
4. **Importers** — the `Importer` protocol and the `CsvImporter` implementation
5. **Exporter Architecture** — the `Exporter` protocol, `CsvExporter`, and `DmnExporter` foundations
6. **DMN XML Construction** — building DMN 1.3 XML element trees
7. **FEEL Expression Mapping** — translating the 11 `MatchStrategy` values to FEEL expressions
8. **Validators and Decomposers** — rule table integrity checks and fragment-based decomposition
9. **CLI Interface** — the Typer-based command-line interface for export, import, validate, and decompose

This syllabus intentionally excludes decision-table design methodology, DMN execution engines and FEEL evaluation, database storage of decision tables, rule versioning and governance workflows, and performance optimization of large rule sets — those topics sit outside the format-translation problem this course addresses.

## Learning Outcomes

After completing this course, a learner will be able to, organized by Bloom's taxonomy level:

**Remember** — List the four plugin extension axes (exporters, importers, decomposers, validators); name the four entry point groups used for plugin discovery; identify the 11 `MatchStrategy` values mapped to FEEL expressions.

**Understand** — Explain how the `PluginRegistry` discovers and loads plugins via entry points; describe the DMN 1.3 XML structure (`definitions`, `decision`, `decisionTable`, `input`, `output`, `rule`); explain the FEEL expression mapping for each `MatchStrategy`.

**Apply** — Import a CSV file into a `Lattice` with dimension inference; export a `Lattice` to DMN 1.3 XML with correct FEEL expressions; run validators against a `Lattice` and interpret the resulting `ValidationReport`.

**Analyze** — Compare the `Exporter`, `Importer`, `Validator`, and `Decomposer` protocol contracts; analyze how dimension metadata drives FEEL expression generation.

**Evaluate** — Assess `ValidationReport` results to determine rule table quality; evaluate when to use decomposition versus monolithic table export.

**Create** — Implement a new `Exporter` plugin conforming to the `Exporter` protocol; build custom validators and register them via entry points; design new `MatchStrategy`-to-FEEL mappings for domain-specific needs.

## Where to Go Next

Begin with [Chapter 1: Foundations](chapters/01-foundations/index.md), or consult the [Learning Graph](learning-graph/index.md) to see how the concepts in each chapter depend on one another before choosing a reading order.

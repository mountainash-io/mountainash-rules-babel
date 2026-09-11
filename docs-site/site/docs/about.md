---
title: 'About'
description: 'About the Mountainash Rules Babel intelligent textbook: scope, authorship, license, and relationship to the mountainash-rules-babel code repository'
---

# About This Book

Mountainash Rules Babel is an intelligent textbook covering **mountainash-rules-babel**, the format translation engine for decision tables and business rules in the mountainash rules ecosystem. It exists to explain, in depth, how a plugin-based Python library moves decision logic between formats — CSV, OMG DMN 1.3 XML with FEEL expressions, and (in future work) GoRules JDM, Drools, InRule, and feature-flag platforms — while preserving the semantics of the rules being translated.

## Scope

This book is a companion to the code, not a replacement for its API reference. It walks through the architecture that makes mountainash-rules-babel extensible: the `PluginRegistry` and its four extension axes (exporters, importers, decomposers, validators), discovery via `importlib.metadata` entry points, the DMN 1.3 XML structure, the mapping from the 11 `MatchStrategy` values to FEEL expressions, the four built-in validators, fragment-based decomposition, and the Typer CLI that ties it all together. It intentionally excludes decision-table design methodology, DMN execution engines, database storage of rule tables, rule governance workflows, and performance tuning of large rule sets — those are separate concerns from format translation itself.

The book assumes intermediate Python (protocols, dataclasses, entry points), a basic understanding of decision tables and business rules, familiarity with XML and CSV, and some prior exposure to the mountainash-rules core package (`Lattice`, `Dimension`, `MatchStrategy`), since mountainash-rules-babel operates on the `Lattice` objects that package defines.

## How to Read This Book

Start at [Chapters](chapters/index.md), which progresses through nine chapters from foundational concepts to plugin infrastructure, importers, exporter architecture, DMN XML construction, FEEL expression mapping, validators and decomposers, and finally the CLI. Each chapter builds on the last, so reading in order is recommended for newcomers; readers already familiar with the plugin architecture can jump directly to the chapters covering DMN construction, FEEL mapping, or validation. The [Learning Graph](learning-graph/index.md) shows how concepts across the book depend on one another, and [MicroSims](sims/index.md) collects interactive simulations that accompany specific chapters.

## Authorship

This textbook is written and maintained by **Nathaniel Ramm**, who is also the author of the mountainash-rules-babel package.

## Relationship to the Code Repository

The mountainash-rules-babel source code lives at [github.com/mountainash-io/mountainash-rules-babel](https://github.com/mountainash-io/mountainash-rules-babel). This textbook is generated and maintained alongside that repository — its diagrams, terminology, and worked examples describe the actual plugin registry, exporters, importers, validators, and CLI shipped in the package, not a hypothetical or simplified design. Use the "Edit" links on each page to view or propose changes to the underlying documentation source.

## License

All content in this book is licensed under [CC BY-NC-SA 4.0](license.md) (Attribution-NonCommercial-ShareAlike 4.0 International) — Copyright &copy; 2026 Nathaniel Ramm. You are free to share and adapt the material with attribution, for non-commercial purposes, under the same license. See the [License](license.md) page for full terms, and [Contact](contact.md) for commercial licensing inquiries.

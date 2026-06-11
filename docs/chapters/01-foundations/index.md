---
title: "Chapter 1: Foundations"
description: "Core concepts for the mountainash-rules-babel translation engine: decision tables, business rules, data formats, DMN, FEEL, and the Lattice object."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 1: Foundations

## Summary

This chapter introduces the foundational concepts required to understand the mountainash-rules-babel translation engine. You will learn about decision tables and business rules as core abstractions, the CSV and XML data formats used for import/export, the OMG DMN 1.3 standard for interchangeable decision models, the FEEL expression language, and the Lattice object that serves as the internal representation.

---

## What Problem Does Babel Solve?

Organizations encode decision logic --- pricing tiers, eligibility criteria, risk classifications --- in dozens of incompatible formats. A compliance team might maintain rules in spreadsheets, while the engineering team needs those same rules in a standards-compliant XML format for a decision engine. Manually converting between formats is tedious, error-prone, and difficult to audit. The mountainash-rules-babel library exists to automate this translation, and understanding the concepts in this chapter is the first step toward using it effectively.

<!-- concept:1 -->
## Decision Tables

A **decision table** is a tabular structure that maps combinations of input conditions to output actions. Each row represents a single rule: when a specific set of conditions is met, a corresponding set of outputs applies. Decision tables have been used in software engineering since the 1960s because they make complex conditional logic explicit and auditable.

Consider a simplified insurance pricing table:

| Age Range | Risk Category | Base Premium |
|-----------|---------------|-------------|
| 18-25     | Low           | 200         |
| 18-25     | High          | 450         |
| 26-40     | Low           | 150         |
| 26-40     | High          | 350         |

The left-hand columns (Age Range, Risk Category) are **input conditions**, and the right-hand column (Base Premium) is the **output action**. Every row is a self-contained rule. The table above contains four rules that together cover all valid combinations of two age ranges and two risk categories.

Decision tables offer several advantages over nested if-else chains:

- **Completeness checking** --- you can verify that every valid input combination has an assigned output.
- **Conflict detection** --- overlapping rules that produce different outputs are immediately visible.
- **Auditability** --- non-technical stakeholders can read and validate the logic directly.

!!! note "Decision Tables vs. Decision Trees"
    Decision tables express the same logic as decision trees but in a flat, row-oriented format. Trees are useful for visualization, while tables are better suited to machine processing, version control, and bulk validation. Babel operates on the tabular form because it maps cleanly onto dataframes and CSV files.

<!-- concept:2 -->
## Business Rules

A **business rule** is a formal statement that constrains or guides a business decision. Business rules are broader than decision tables: they include policies ("customers under 18 require parental consent"), calculations ("discount = base_price * loyalty_factor"), and constraints ("order total must not exceed credit limit"). Decision tables are one way to encode business rules, particularly when the logic follows a pattern of "given these conditions, apply this action."

In the mountainash ecosystem, business rules are represented as structured data rather than procedural code. This separation of concerns allows rules to be:

- Authored by domain experts who may not write code
- Versioned and audited alongside the data they govern
- Translated between formats without rewriting application logic

The babel library focuses specifically on the **format translation** aspect of this lifecycle. It does not evaluate or execute rules; instead, it converts them between representations so that different tools in the pipeline can consume them.

#### Diagram: Business Rules Lifecycle

<iframe src="../../sims/business-rules-lifecycle/main.html" width="100%" height="500px" scrolling="no"></iframe>
<details markdown="1">
<summary>Business Rules Lifecycle</summary>
Type: workflow
**sim-id:** business-rules-lifecycle<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show the lifecycle of a business rule from authoring through translation to execution, highlighting where babel sits in the pipeline.

**Components:** Nodes for Author (domain expert), CSV/Spreadsheet, Babel Translator, DMN XML, Decision Engine, and Application. Directed edges show the flow: Author creates CSV, Babel translates CSV to DMN, Decision Engine loads DMN, Application queries the engine.

**Interactions:** Hover over each node to see a tooltip describing its role. Click a node to highlight all edges connected to it. Drag nodes to rearrange the layout.

**Colors:** Author node in blue, format nodes (CSV, DMN) in green, Babel in orange, engine/application in purple.

**Learning Objective:** Understand where format translation fits in the business rules lifecycle (Bloom: Understand).
</details>

<!-- concept:3 -->
<!-- concept:4 -->
## CSV Format

**CSV** (Comma-Separated Values) is a plain-text format where each line represents a record and fields within a record are separated by commas. CSV files are the primary import format for babel because they are the natural output of spreadsheet tools and are easy to inspect with any text editor.

A typical decision table in CSV looks like this:

```csv
age_range,risk_category,base_premium
18-25,Low,200
18-25,High,450
26-40,Low,150
26-40,High,350
```

The first row contains column headers. Subsequent rows contain data values. Babel uses the Polars library to parse CSV files because Polars provides fast, type-aware column inference and handles edge cases such as quoted fields, mixed encodings, and large files efficiently.

Key properties of CSV that matter for babel:

- **No schema** --- CSV files do not carry metadata about which columns are inputs vs. outputs, what data types columns contain, or what match strategy applies. Babel must infer or be told these details.
- **Universal readability** --- every programming language, spreadsheet tool, and database can produce and consume CSV.
- **Row-oriented** --- each row is a complete rule, which maps directly to the decision table abstraction.

## XML Format

**XML** (Extensible Markup Language) is a hierarchical, tag-based data format. Unlike CSV, XML supports nested structures, namespaces, and schemas that define valid document structure. Babel uses XML as the output format for DMN exports because the DMN standard specifies an XML serialization.

A minimal XML fragment illustrating the structure:

```xml
<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/">
  <decision id="pricing" name="InsurancePricing">
    <decisionTable id="dt_pricing" hitPolicy="UNIQUE">
      <input id="input_age" label="age_range">
        <inputExpression typeRef="string">
          <text>age_range</text>
        </inputExpression>
      </input>
      <!-- outputs and rules follow -->
    </decisionTable>
  </decision>
</definitions>
```

XML provides capabilities that CSV lacks, as summarized below:

| Feature | CSV | XML |
|---------|-----|-----|
| Nested structure | No | Yes |
| Data types | Inferred | Declared via `typeRef` |
| Namespaces | No | Yes (e.g., DMN namespace) |
| Schema validation | No | Yes (XSD, Schematron) |
| Human readability | High | Moderate |
| File size | Compact | Verbose |

Babel reads CSV and writes XML (among other formats). The XML Security Module ensures that generated XML documents are safe to parse by disabling entity resolution, which prevents XML External Entity (XXE) injection attacks.

<!-- concept:5 -->
## DMN Standard

The **Decision Model and Notation** (DMN) standard is published by the Object Management Group (OMG). Version 1.3, which babel targets, defines both a visual notation for decision models and an XML interchange format. DMN provides a vendor-neutral way to describe decision logic so that models authored in one tool can be executed in another.

DMN organizes decision logic into a hierarchy of elements:

1. **Definitions** --- the root container for all elements in a DMN model
2. **Decision** --- a named decision point (e.g., "Determine Insurance Premium")
3. **DecisionTable** --- the tabular logic within a decision, specifying inputs, outputs, and rules
4. **Input / Output** --- column definitions with type information
5. **Rule** --- a single row of the decision table, containing input entries and output entries

#### Diagram: DMN Element Hierarchy

<iframe src="../../sims/dmn-element-hierarchy/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>DMN Element Hierarchy</summary>
Type: diagram
**sim-id:** dmn-element-hierarchy<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Visualize the parent-child nesting of DMN XML elements from Definitions down to Rule entries.

**Components:** Tree layout with nodes for Definitions, Decision, DecisionTable, Input, Output, Rule, InputEntry, and OutputEntry. Edges show containment (parent to child).

**Interactions:** Click any node to expand/collapse its children. Hover to see a description of that element's role in the DMN specification. Drag to rearrange.

**Colors:** Root (Definitions) in steel blue, Decision in dark blue, DecisionTable in teal, Input/Output in green/red, Rule in gold.

**Learning Objective:** Recall the hierarchical structure of a DMN XML document (Bloom: Remember).
</details>

The DMN standard also specifies a **hit policy** that determines how the decision engine handles overlapping rules. Babel sets the hit policy to `UNIQUE` by default, meaning each input combination must match exactly one rule. Other hit policies (FIRST, PRIORITY, COLLECT) exist in the specification but are not currently generated by babel's exporter.

<!-- concept:6 -->
## FEEL Language

**FEEL** (Friendly Enough Expression Language) is the expression language defined by the DMN standard. FEEL expressions appear inside the `<text>` elements of input entries and output entries in a DMN decision table. They define the matching conditions for each cell.

FEEL was designed to be readable by business analysts while remaining precise enough for machine evaluation. The following table illustrates several FEEL expressions and their meanings:

| FEEL Expression | Meaning |
|----------------|---------|
| `"Gold"` | Exact match on the string "Gold" |
| `> 100` | Greater than 100 |
| `[18..25]` | In the range 18 to 25, inclusive |
| `not("Rejected")` | Any value except "Rejected" |
| `starts with(?, "AU")` | String starts with "AU" |
| (empty string) | Any value matches (wildcard) |

Babel translates between internal match strategies (such as `MatchStrategy.EXACT`, `MatchStrategy.GREATER_THAN`, `MatchStrategy.RANGE`) and their corresponding FEEL expressions. This translation is a critical part of the DMN export pipeline and is covered in depth in Chapter 7.

FEEL supports both **S-FEEL** (a simplified subset for decision table cells) and **full FEEL** (a complete expression language with functions, contexts, and lists). Babel generates S-FEEL expressions because decision table cells only require the simpler subset.

#### Diagram: Match Strategy to FEEL Mapping

<iframe src="../../sims/match-strategy-feel-map/main.html" width="100%" height="400px" scrolling="no"></iframe>
<details markdown="1">
<summary>Match Strategy to FEEL Mapping</summary>
Type: chart
**sim-id:** match-strategy-feel-map<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show the correspondence between internal MatchStrategy enum values and FEEL expression patterns.

**Components:** Two-column layout with MatchStrategy values on the left (EXACT, NOT_EQUAL, RANGE, GREATER_THAN, LESS_THAN, PREFIX, SUFFIX, CONTAINS, SET_MEMBERSHIP, SET_EXCLUSION) connected by arrows to their FEEL output patterns on the right.

**Interactions:** Hover over a MatchStrategy node to highlight its corresponding FEEL pattern and show an example. Click to toggle a detailed explanation panel.

**Colors:** MatchStrategy nodes in dark slate blue, FEEL pattern nodes in crimson, connecting arrows in gray.

**Learning Objective:** Understand how internal match strategies map to FEEL expressions (Bloom: Understand).
</details>

<!-- concept:10 -->
## Lattice Object

The **Lattice** is the central data structure in the mountainash-rules ecosystem. It serves as the **internal representation** that all babel operations work with. When you import a CSV file, babel produces a Lattice. When you export to DMN, babel reads from a Lattice. The Lattice is the lingua franca that decouples importers from exporters.

A Lattice bundles four pieces of information:

- **dataframe** --- the actual rule data, stored as a Polars DataFrame where each row is a rule and each column is either an input dimension or an output aggregate
- **metadata** --- a `DimensionsMetadata` object that describes each input dimension, including its name, data type, and match strategy
- **aggregates** --- a list of `Aggregate` objects describing the output columns and any aggregation operations
- **partition_key** --- an optional key for splitting a large table into independent sub-tables

The relationship between these components can be understood through a concrete example. Given the insurance CSV from earlier, a Lattice would contain:

```python
Lattice(
    dataframe=polars.DataFrame({
        "age_range": ["18-25", "18-25", "26-40", "26-40"],
        "risk_category": ["Low", "High", "Low", "High"],
        "base_premium": [200, 450, 150, 350],
    }),
    metadata=DimensionsMetadata(dimensions=[
        Dimension(name="age_range", match_strategy=EXACT, data_type=str),
        Dimension(name="risk_category", match_strategy=EXACT, data_type=str),
    ]),
    aggregates=[Aggregate(column_name="base_premium", operation="assign")],
    partition_key=None,
)
```

The Lattice design follows the **canonical intermediate representation** pattern common in compilers and translators. Just as a compiler converts source code to an intermediate representation (IR) before generating machine code, babel converts input formats to a Lattice before generating output formats. This architecture means that adding a new input format requires writing only one importer (format to Lattice), and adding a new output format requires writing only one exporter (Lattice to format), rather than writing \( n \times m \) converters for every pair of formats.

#### Diagram: Lattice as Intermediate Representation

<iframe src="../../sims/lattice-ir-architecture/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>Lattice as Intermediate Representation</summary>
Type: infographic
**sim-id:** lattice-ir-architecture<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Illustrate how the Lattice object decouples importers from exporters, avoiding the N x M converter problem.

**Components:** Left column: importer nodes (CSV Importer, future JSON Importer, future Excel Importer). Center: single Lattice node. Right column: exporter nodes (CSV Exporter, DMN Exporter, future JSON Exporter). Arrows from each importer to the Lattice, and from the Lattice to each exporter.

**Interactions:** Click the Lattice node to see its internal structure (dataframe, metadata, aggregates, partition_key). Hover over any importer/exporter to see what format it handles. Click an importer to animate a data flow arrow from it through the Lattice to all exporters.

**Colors:** Importers in dark green, Lattice in steel blue, Exporters in crimson. Future/planned nodes shown with dashed borders.

**Learning Objective:** Analyze how the intermediate representation pattern reduces the number of format converters needed (Bloom: Analyze).
</details>

Understanding the Lattice is essential because every subsequent chapter assumes you know what it contains and how importers produce it and exporters consume it. The metadata within the Lattice --- particularly the `match_strategy` on each dimension --- drives the FEEL expression generation covered in Chapter 7 and the validation logic covered in Chapter 8.

## Key Takeaways

- **Decision tables** are a tabular format for encoding conditional business logic, where each row maps input conditions to output actions.
- **Business rules** are formal statements that guide decisions; decision tables are one encoding of business rules, and babel translates between encodings without executing the rules.
- **CSV** is the primary import format because it is universal, human-readable, and maps naturally to decision table rows.
- **XML** is the primary export format for DMN because the DMN standard specifies an XML serialization with namespaces, type declarations, and nested element structure.
- **DMN 1.3** (Decision Model and Notation) is the OMG standard that defines both a visual notation and an XML interchange format for decision models.
- **FEEL** (Friendly Enough Expression Language) is the expression language within DMN that specifies matching conditions in decision table cells.
- **The Lattice** is babel's canonical intermediate representation, bundling a Polars DataFrame with dimension metadata, aggregates, and an optional partition key to decouple importers from exporters.
- The **intermediate representation pattern** means adding a new format requires writing only one plugin (importer or exporter), not a converter for every existing format pair.

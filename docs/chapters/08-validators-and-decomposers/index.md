---
title: "Chapter 8: Validators and Decomposers"
description: "The Validator and Decomposer protocols, structured reporting with ValidationIssue and ValidationReport, four built-in validators, and the Fragment/DecompositionResult dataclasses."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 8: Validators and Decomposers

## Summary

This chapter covers the validation and decomposition subsystems. You will learn the Validator protocol contract, the ValidationIssue and ValidationReport dataclasses for structured reporting, and the four built-in validators (conflicts, coverage, orphans, round-trip). It also introduces the Decomposer protocol with its Fragment and DecompositionResult dataclasses for splitting complex tables into normalized fragments.

## Concepts Covered

- Validator Protocol
- ValidationIssue Dataclass
- ValidationReport Dataclass
- ConflictsValidator
- CoverageValidator
- OrphansValidator
- RoundTripValidator
- Decomposer Protocol
- Fragment Dataclass
- DecompositionResult Dataclass
- ValidationError Class

## Prerequisites

- Chapter 1: Foundations (Lattice Object)
- Chapter 2: Python Plugin Infrastructure (Runtime Checkable Protocol)
- Chapter 3: Plugin Extension Points (Validator Entry Points, Decomposer Entry Points, BabelError Base)

---

## Quality Assurance in the Translation Pipeline

Format translation is not just about producing syntactically correct output. A decision table might be well-formed XML yet contain logical errors --- overlapping rules that produce contradictory outputs, gaps in coverage where no rule applies, or rules that can never fire because they are shadowed by others. Babel's validation subsystem provides structured checks for these issues, while the decomposition subsystem addresses complexity by splitting large tables into manageable, focused fragments.

<!-- concept:54 -->
<!-- concept:61 -->
## Validator Protocol

The **Validator protocol** defines the contract for all validation plugins. Like the Importer and Exporter protocols, it uses `@runtime_checkable` to enable runtime type checking:

```python
@runtime_checkable
class Validator(Protocol):
    name: str

    def validate(self, lattice: Lattice, **options) -> ValidationReport: ...
```

The protocol is the simplest in babel: just a name attribute and a single method. The `validate` method accepts a Lattice and returns a `ValidationReport` describing any issues found. The `**options` parameter allows validator-specific configuration (e.g., tolerance thresholds for coverage analysis).

This design means validators are purely diagnostic --- they inspect the Lattice but never modify it. They report problems; they do not fix them. This separation of concerns keeps the validation logic focused and testable.

<!-- concept:55 -->
<!-- concept:56 -->
<!-- concept:62 -->
<!-- concept:63 -->
<!-- concept:70 -->
## ValidationIssue Dataclass

A **ValidationIssue** represents a single problem or observation found during validation. It is a Python dataclass with four fields:

```python
@dataclass
class ValidationIssue:
    severity: Literal["error", "warning", "info"]
    category: str
    message: str
    details: dict | None = None
```

The fields serve distinct purposes:

- **severity** --- one of three levels: `"error"` (the table is invalid and should not be used), `"warning"` (potential problem that may be intentional), or `"info"` (informational observation)
- **category** --- a machine-readable tag identifying the type of issue (e.g., `"conflict"`, `"gap"`, `"orphan"`, `"not_implemented"`)
- **message** --- a human-readable description of the issue
- **details** --- an optional dictionary with structured data about the issue (e.g., which rows conflict, which input combinations have no coverage)

The severity hierarchy enables filtering:

| Severity | Meaning | Effect on is_valid |
|----------|---------|-------------------|
| `error` | Table is logically invalid | Sets `is_valid = False` |
| `warning` | Potential issue, may be intentional | Does not affect `is_valid` |
| `info` | Observation, no action needed | Does not affect `is_valid` |

## ValidationReport Dataclass

A **ValidationReport** aggregates all issues from a validation run into a single structured object. It carries both the issue list and summary statistics:

```python
@dataclass
class ValidationReport:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    input_row_count: int | None = None
    output_row_count: int | None = None
    exact_match: bool | None = None
    fragment_count: int | None = None
    combination_count: int | None = None
    conflict_count: int = 0
    coverage_gap_count: int = 0
    orphan_count: int = 0
```

The report provides two convenience properties for filtering issues by severity:

```python
@property
def errors(self) -> list[ValidationIssue]:
    return [i for i in self.issues if i.severity == "error"]

@property
def warnings(self) -> list[ValidationIssue]:
    return [i for i in self.issues if i.severity == "warning"]
```

When the public `validate()` API aggregates results from multiple validators, it constructs a combined report where `is_valid` is `True` only if no issues have severity `"error"` and no issues have category `"not_implemented"`:

```python
is_valid = all(issue.severity != "error" for issue in all_issues)
has_not_implemented = any(issue.category == "not_implemented" for issue in all_issues)
if has_not_implemented:
    is_valid = False
```

This means a report with only warnings is still considered valid, but a report containing any `"not_implemented"` category (indicating the validator could not actually perform its check) is considered invalid as a safety measure.

#### Diagram: Validation Report Structure

<iframe src="../../sims/validation-report-structure/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>Validation Report Structure</summary>
Type: diagram
**sim-id:** validation-report-structure<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show the relationship between ValidationReport, ValidationIssue, severity levels, and the is_valid determination logic.

**Components:** Central ValidationReport node with fields as labeled ports. Connected ValidationIssue nodes showing different severities (color-coded). Decision logic flow from issues list through severity/category checks to the is_valid boolean. Properties (errors, warnings) shown as derived accessor nodes.

**Interactions:** Click a severity level to filter the visible issues. Hover over the is_valid node to see the determination logic. Click "Add Issue" buttons to see how different issue types affect the report.

**Colors:** Error issues in crimson, warning issues in gold, info issues in steel blue, is_valid=True in green, is_valid=False in red.

**Learning Objective:** Evaluate how different issue combinations affect the overall validity determination (Bloom: Evaluate).
</details>

<!-- concept:57 -->
## ConflictsValidator

The **ConflictsValidator** checks for overlapping rules that produce different outputs for the same input combination. A conflict means two or more rules could match the same input, and they disagree about what the output should be. This violates the UNIQUE hit policy assumption that babel uses for DMN export.

```python
class ConflictsValidator:
    name: str = "conflicts"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        # Currently returns not_implemented status
```

The validator is registered as a plugin and discoverable via the entry point system. Its current implementation returns a `"not_implemented"` warning, indicating that the logic for detecting conflicts is planned but not yet active. When fully implemented, it will compare all row pairs and identify cases where input dimensions match but output columns differ.

Conceptually, a conflict occurs when two rules overlap in their input space:

- Rule 1: age=18-25 AND risk=High THEN premium=450
- Rule 2: age=18-25 AND risk=High THEN premium=500

These rules have identical input conditions but different outputs --- a conflict that would cause ambiguous behavior in a decision engine.

<!-- concept:58 -->
## CoverageValidator

The **CoverageValidator** checks whether every valid input combination is handled by at least one rule. A coverage gap means there exist input values for which no rule would fire, potentially causing a decision engine to return no result or throw an error.

```python
class CoverageValidator:
    name: str = "coverage"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        # Currently returns not_implemented status
```

Complete coverage is especially important for decision tables with enumerable domains. If a dimension has three possible values (Low, Medium, High) and another has two (Yes, No), full coverage requires \( 3 \times 2 = 6 \) rules. If only 5 are present, the CoverageValidator would identify the missing combination.

<!-- concept:59 -->
## OrphansValidator

The **OrphansValidator** checks for rules that can never fire because their conditions are completely subsumed by other rules with higher priority or more general matching. An orphan rule is dead code in the decision table --- it increases complexity without contributing to the decision logic.

```python
class OrphansValidator:
    name: str = "orphans"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        # Currently returns not_implemented status
```

Orphan detection is particularly relevant when tables evolve over time. As new rules are added, older rules may become unreachable. Without automatic detection, these dead rules accumulate and make the table harder to understand and maintain.

<!-- concept:60 -->
## RoundTripValidator

The **RoundTripValidator** checks whether exporting a Lattice and re-importing it produces the same data. This validates that the export process is lossless (for formats that can represent the full Lattice) or identifies what information is lost (for lossy formats like CSV that cannot represent metadata).

```python
class RoundTripValidator:
    name: str = "round_trip"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        # Currently returns not_implemented status
```

Round-trip validation is triggered automatically by the `export_lattice` function when called with `validate=True`:

```python
result = babel.export_lattice(lattice, "dmn", path=output, validate=True)
```

When fully implemented, this validator will export the Lattice, re-import the output, and compare the resulting Lattice with the original. Differences in row count, column values, or metadata indicate export bugs or format limitations.

The four validators together cover the four major quality dimensions of a decision table:

| Validator | Quality Dimension | Question Answered |
|-----------|------------------|-------------------|
| conflicts | Consistency | Do any rules contradict each other? |
| coverage | Completeness | Is every valid input handled? |
| orphans | Minimality | Are there unreachable rules? |
| round_trip | Fidelity | Does export preserve the data? |

## Decomposer Protocol

The **Decomposer protocol** defines the contract for plugins that split complex decision tables into simpler fragments. Decomposition is the reverse of composition: it takes one large table and produces multiple smaller, focused tables that are easier to understand, test, and maintain.

```python
@runtime_checkable
class Decomposer(Protocol):
    name: str

    def decompose(self, lattice: Lattice, **options) -> DecompositionResult: ...
```

The protocol follows the same pattern as the Validator protocol --- a name attribute and a single method. The difference is the return type: instead of a ValidationReport, a Decomposer returns a DecompositionResult containing the fragments.

Decomposition is useful when a single decision table combines logically independent concerns. For example, a table might mix geographic pricing rules with product-category rules. Decomposing it into separate geographic and product tables makes each one easier to reason about and reduces the combinatorial explosion of rows.

#### Diagram: Decomposition Concept

<iframe src="../../sims/decomposition-concept/main.html" width="100%" height="450px" scrolling="no"></iframe>
<details markdown="1">
<summary>Decomposition Concept</summary>
Type: infographic
**sim-id:** decomposition-concept<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Illustrate how a large decision table with mixed concerns is decomposed into smaller, focused fragments.

**Components:** Left side: single large table node (12 rows, 5 columns, mixed concerns). Arrow labeled "decompose()" points right to three smaller fragment nodes (Fragment A: 4 rows, geographic rules; Fragment B: 3 rows, product rules; Fragment C: 5 rows, temporal rules). Annotations show row count reduction and concern separation.

**Interactions:** Click the large table to see its sample content. Click each fragment to see its focused subset. Hover over the decompose arrow to see the algorithm description. Toggle "show dimension groups" to see which columns go to which fragment.

**Colors:** Original table in orange, fragments in different shades of teal/green/blue, decompose arrow in dark slate blue.

**Learning Objective:** Understand why and when decomposition improves decision table quality (Bloom: Understand).
</details>

## Fragment Dataclass

A **Fragment** represents one piece of a decomposed decision table. It contains the subset of data and metadata that belongs to one logical concern:

```python
@dataclass
class Fragment:
    name: str
    dataframe: Any
    dimensions: list[str]
    metadata: DimensionsMetadata
    aggregates: list[Aggregate]
    source_rows: list[int] | None = None
```

The fields describe the fragment completely:

- **name** --- a human-readable identifier for this fragment (e.g., "geographic_rules")
- **dataframe** --- the subset of rows belonging to this fragment
- **dimensions** --- the dimension column names relevant to this fragment
- **metadata** --- full DimensionsMetadata for the fragment's dimensions
- **aggregates** --- the output columns included in this fragment
- **source_rows** --- optional list of row indices in the original table, enabling traceability

The `source_rows` field is important for auditability. When a decomposed fragment is modified, the source_rows mapping allows changes to be traced back to specific rows in the original table.

## DecompositionResult Dataclass

A **DecompositionResult** bundles all fragments with summary information about the decomposition:

```python
@dataclass
class DecompositionResult:
    fragments: list[Fragment]
    metadata: DimensionsMetadata
    aggregates: list[Aggregate]
    original_row_count: int
    fragment_count: int
    dimension_groups: list[list[str]]
    validation: ValidationReport | None = None
```

Key fields beyond the fragment list:

- **original_row_count** --- how many rows the input table had (for size comparison)
- **fragment_count** --- number of fragments produced (convenience field, same as `len(fragments)`)
- **dimension_groups** --- which dimensions were grouped together in each fragment, revealing the decomposition's structural decisions
- **validation** --- an optional ValidationReport that the decomposer can attach to report quality issues found during decomposition

The `dimension_groups` field is particularly valuable for understanding the decomposer's decisions. If a table has dimensions A, B, C, D and the decomposer produces groups `[["A", "B"], ["C", "D"]]`, this means dimensions A and B are interdependent (they must be evaluated together) while C and D form an independent concern.

## ValidationError Class

The **ValidationError** class bridges the validation and error handling subsystems. It is raised when a validation failure should halt processing (as opposed to being reported for informational purposes):

```python
class ValidationError(BabelError):
    def __init__(self, message: str, report: ValidationReport | None = None) -> None:
        self.report = report
        super().__init__(message)
```

Unlike the validators themselves (which return reports), the ValidationError is raised by higher-level functions that use validation as a gate. The `export_lattice` function with `validate=True`, for example, raises ValidationError if the round-trip check fails:

```python
if validate:
    report = _run_validators(lattice, ["round_trip"])
    if not report.is_valid and report.errors:
        raise ValidationError("Validation failed after export", report=report)
```

The error carries the full ValidationReport as an attribute, allowing calling code to inspect the specific issues that caused the failure:

```python
try:
    babel.export_lattice(lattice, "dmn", validate=True)
except ValidationError as e:
    for issue in e.report.errors:
        print(f"  {issue.category}: {issue.message}")
```

!!! warning "Validators Are Currently Stubbed"
    All four built-in validators currently return `"not_implemented"` status. They are registered and discoverable but do not perform actual analysis yet. The infrastructure is complete; the detection algorithms are pending implementation. This means `validate=True` on exports will always raise ValidationError in the current version.

## Key Takeaways

- The **Validator protocol** defines a simple `validate(lattice) -> ValidationReport` contract for quality checks.
- **ValidationIssue** captures a single problem with severity (error/warning/info), category, message, and optional structured details.
- **ValidationReport** aggregates issues and determines overall validity --- any error-severity issue or `"not_implemented"` category makes the report invalid.
- **ConflictsValidator** detects overlapping rules with contradictory outputs (consistency check).
- **CoverageValidator** identifies input combinations with no matching rule (completeness check).
- **OrphansValidator** finds unreachable rules that can never fire (minimality check).
- **RoundTripValidator** verifies export/re-import fidelity (lossless translation check).
- The **Decomposer protocol** defines a `decompose(lattice) -> DecompositionResult` contract for table splitting.
- **Fragment** represents one piece of a decomposed table with its data, metadata, and source row traceability.
- **DecompositionResult** bundles fragments with summary statistics and optional validation results.
- **ValidationError** is raised when validation failure should halt processing, carrying the full report for programmatic inspection.

---
title: "Chapter 6: DMN XML Construction"
description: "How the DmnExporter builds a DMN 1.3 XML document element by element, from Definitions through Rules, plus the XML Security Module."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 6: DMN XML Construction

## Summary

This chapter details how the DmnExporter builds a complete DMN 1.3 XML document. You will learn the hierarchical element structure --- from the root Definitions element through Decision, DecisionTable, Input, Output, and Rule elements --- and how the XML Security Module ensures safe serialization with entity resolution disabled.

---

## Building XML from the Inside Out

The DmnExporter's `export_bytes` method constructs a DMN 1.3 XML document programmatically using the lxml library's `etree` module. Rather than writing XML as text (which is fragile and error-prone), babel builds an in-memory element tree and serializes it at the end. This approach guarantees well-formed XML, correct namespace handling, and proper character escaping.

The construction follows the DMN element hierarchy top-down: Definitions contains Decision, Decision contains DecisionTable, and DecisionTable contains Input, Output, and Rule elements. Understanding each layer is essential for debugging export output or extending the exporter.

<!-- concept:34 -->
## DMN XML Tree Construction

The **DMN XML tree construction** process begins with a conversion step and a classification step before any XML elements are created. The DmnExporter first converts the Lattice's data to a Polars DataFrame, then classifies columns into dimensions (inputs) and outputs:

```python
df = _to_polars(lattice)
dim_names = {d.dimension_name for d in lattice.metadata.dimensions}

# Identify range helper columns to skip
range_extra_cols: set[str] = set()
for dim in lattice.metadata.dimensions:
    if dim.match_strategy == MatchStrategy.RANGE:
        if dim.range_min_field:
            range_extra_cols.add(dim.range_min_field)
        if dim.range_max_field:
            range_extra_cols.add(dim.range_max_field)

<!-- concept:39 -->
# Output columns = everything that isn't a dimension, range helper, or rule_name
output_cols = [
    c for c in df.columns
    if c not in dim_names
    and c not in range_extra_cols
    and c != "rule_name"
]
```

Range dimensions deserve special attention. A range-typed dimension (e.g., "age between 18 and 25") may use two DataFrame columns --- one for the minimum and one for the maximum. These helper columns should not appear as separate DMN inputs or outputs, so they are excluded from `output_cols`. The actual range values are consumed later when building FEEL range expressions.

The column classification step produces two clean lists:

- **Input dimensions** from `lattice.metadata.dimensions` (with order preserved)
- **Output columns** from the remaining DataFrame columns

#### Diagram: Column Classification Logic

<iframe src="../../sims/column-classification/main.html" width="100%" height="400px" scrolling="no"></iframe>
<details markdown="1">
<summary>Column Classification Logic</summary>
Type: workflow
**sim-id:** column-classification<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show how DataFrame columns are classified into dimensions, outputs, range helpers, and excluded metadata columns.

**Components:** Starting node: "All DataFrame Columns." Decision diamonds: "Is dimension?", "Is range helper?", "Is rule_name?" Terminal nodes: "Input Dimension", "Output Column", "Excluded (range helper)", "Excluded (metadata)." Sample columns flow through the decision tree.

**Interactions:** Click a decision diamond to see the Python expression that implements that check. Hover over terminal nodes to see how each category is used downstream. Toggle example dataset to see real columns flowing through.

**Colors:** Dimension path in dark green, output path in crimson, excluded paths in gray.

**Learning Objective:** Apply the column classification logic to predict how a given DataFrame's columns will be categorized (Bloom: Apply).
</details>

<!-- concept:35 -->
<!-- concept:36 -->
<!-- concept:37 -->
## DMN Definitions Element

The **Definitions element** is the root of every DMN XML document. It carries the DMN namespace declaration, a unique identifier, a human-readable name, and a namespace URI for the model itself:

```python
definitions = etree.Element("definitions", nsmap=NSMAP)
definitions.set("id", "definitions_babel")
definitions.set("name", decision_name)
definitions.set("namespace", "https://mountainash.io/babel")
```

The `nsmap=NSMAP` parameter sets the default namespace to the DMN 1.3 namespace URI (`https://www.omg.org/spec/DMN/20191111/MODEL/`). This means all child elements inherit this namespace without requiring a prefix.

The Definitions element's attributes serve specific purposes in the DMN ecosystem:

| Attribute | Value | Purpose |
|-----------|-------|---------|
| `id` | `"definitions_babel"` | Unique identifier for XML cross-references |
| `name` | From `decision_name` option | Human-readable label shown in modeling tools |
| `namespace` | `"https://mountainash.io/babel"` | Model-specific namespace (distinct from the DMN spec namespace) |

The `decision_name` value comes from the `**options` passed to `export_bytes`, defaulting to `"GeneratedDecision"` if not specified. This allows users to control the naming of their DMN model without modifying the export code.

## DMN Decision Element

The **Decision element** is a child of Definitions and represents a single decision point in the model. Babel creates one Decision element per export, containing a single DecisionTable:

```python
decision = etree.SubElement(definitions, f"{{{DMN_NS}}}decision")
decision.set("id", f"decision_{table_name}")
decision.set("name", decision_name)
```

The `f"{{{DMN_NS}}}decision"` syntax is an lxml convention for creating elements in a specific namespace. The triple braces are necessary because:

- The outer `{}` pair is the f-string delimiter
- The inner `{DMN_NS}` is the actual namespace URI enclosed in lxml's namespace syntax

The Decision element in DMN can contain multiple types of logic (decision tables, literal expressions, invocations), but babel always creates a DecisionTable because the Lattice abstraction corresponds directly to a tabular decision.

## DMN DecisionTable Element

The **DecisionTable element** is the container for the actual decision logic. It holds Input, Output, and Rule elements. Babel configures it with a `hitPolicy` of `UNIQUE`, meaning each input combination must match at most one rule:

```python
dt = etree.SubElement(decision, f"{{{DMN_NS}}}decisionTable")
dt.set("id", f"dt_{table_name}")
dt.set("hitPolicy", "UNIQUE")
```

The DMN specification defines several hit policies that control how overlapping rules are handled:

| Hit Policy | Behavior | Babel Support |
|-----------|----------|---------------|
| UNIQUE | At most one rule matches; error if multiple match | Default (generated) |
| FIRST | First matching rule wins (order-dependent) | Not generated |
| PRIORITY | Highest-priority matching rule wins | Not generated |
| ANY | All matching rules must agree on output | Not generated |
| COLLECT | All matching rules contribute to output list | Not generated |

Babel uses UNIQUE because it matches the semantics of well-formed decision tables where each input combination maps to exactly one output. The ConflictsValidator (Chapter 8) checks for violations of this assumption before export.

<!-- concept:38 -->
<!-- concept:40 -->
## DMN Input Elements

**Input elements** define the input columns of the decision table. Babel creates one Input element per dimension in the Lattice's metadata. Each Input contains an InputExpression that specifies the column name and data type:

```python
for dim in lattice.metadata.dimensions:
    inp = etree.SubElement(dt, f"{{{DMN_NS}}}input")
    inp.set("id", f"input_{dim.dimension_name}")
    inp.set("label", dim.dimension_name)

    inp_expr = etree.SubElement(inp, f"{{{DMN_NS}}}inputExpression")
    inp_expr.set("id", f"inputExpr_{dim.dimension_name}")
    inp_expr.set("typeRef", _type_ref(dim.data_type))

    text_el = etree.SubElement(inp_expr, f"{{{DMN_NS}}}text")
    text_el.text = dim.dimension_name
```

The `_type_ref` helper function maps Python types to DMN type references. The mapping is simple:

```python
def _type_ref(data_type: type) -> str:
    if data_type in (int, float):
        return "number"
    return "string"
```

DMN uses `"number"` for both integers and floating-point values, and `"string"` for everything else. This coarse mapping aligns with how FEEL expressions handle types --- numeric comparisons vs. string operations.

The nested structure of an Input element in the generated XML looks like:

```xml
<input id="input_age_range" label="age_range">
  <inputExpression id="inputExpr_age_range" typeRef="string">
    <text>age_range</text>
  </inputExpression>
</input>
```

## DMN Output Elements

**Output elements** define the output columns of the decision table. They are simpler than Input elements because they do not require an expression --- they just declare the output column's name:

```python
for col in output_cols:
    out = etree.SubElement(dt, f"{{{DMN_NS}}}output")
    out.set("id", f"output_{col}")
    out.set("label", col)
    out.set("name", col)
```

Each Output element has three attributes: `id` for XML identification, `label` for human-readable display in modeling tools, and `name` for programmatic reference. In babel's implementation, `label` and `name` are set to the same value (the column name from the DataFrame).

## DMN Rule Elements

**Rule elements** are the heart of the decision table. Each Rule corresponds to one row in the Lattice's DataFrame and contains an InputEntry for each dimension and an OutputEntry for each output column:

```python
rows = df.to_dicts()
for row_idx, row in enumerate(rows):
    rule_el = etree.SubElement(dt, f"{{{DMN_NS}}}rule")
    rule_el.set("id", f"rule_{row_idx}")

    # Input entries
    for dim in lattice.metadata.dimensions:
        ie = etree.SubElement(rule_el, f"{{{DMN_NS}}}inputEntry")
        ie.set("id", f"ie_{row_idx}_{dim.dimension_name}")
        text_el = etree.SubElement(ie, f"{{{DMN_NS}}}text")

        if dim.match_strategy == MatchStrategy.RANGE:
            text_el.text = _feel_range_entry(row, dim)
        else:
            text_el.text = _feel_entry(row.get(dim.dimension_name), dim)

    # Output entries
    for col in output_cols:
        oe = etree.SubElement(rule_el, f"{{{DMN_NS}}}outputEntry")
        oe.set("id", f"oe_{row_idx}_{col}")
        text_el = etree.SubElement(oe, f"{{{DMN_NS}}}text")
        text_el.text = "" if row.get(col) is None else str(row.get(col))
```

The `_feel_entry` and `_feel_range_entry` functions translate cell values into FEEL expressions based on the dimension's match strategy. These are covered in detail in Chapter 7. For now, the important point is that each input cell becomes a FEEL expression string inside a `<text>` element, while each output cell becomes a simple string representation.

The DataFrame is converted to a list of dictionaries (`df.to_dicts()`) so that each row can be accessed by column name. This makes the per-cell lookup straightforward: `row.get(dim.dimension_name)` retrieves the value for a given dimension, and `row.get(col)` retrieves an output value.

#### Diagram: DMN XML Tree Structure

<iframe src="../../sims/dmn-xml-tree-structure/main.html" width="100%" height="550px" scrolling="no"></iframe>
<details markdown="1">
<summary>DMN XML Tree Structure</summary>
Type: diagram
**sim-id:** dmn-xml-tree-structure<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Visualize the complete DMN XML tree for a sample 2-input, 1-output, 4-rule decision table, showing every element with its attributes and text content.

**Components:** Hierarchical tree: Definitions at root, containing Decision, containing DecisionTable, containing two Input elements, one Output element, and four Rule elements. Each Rule expands to show its InputEntry and OutputEntry children with FEEL text content. Attributes shown as labels on each node.

**Interactions:** Click any element node to see its raw XML representation. Hover to see which Python code line creates this element. Collapse/expand subtrees by clicking the toggle icon. Color legend toggle shows namespace vs. no-namespace elements.

**Colors:** Definitions in steel blue, Decision in dark blue, DecisionTable in teal, Input elements in dark green, Output elements in crimson, Rule elements in gold, text content in dark gray.

**Learning Objective:** Analyze the complete structure of a DMN XML document generated by babel (Bloom: Analyze).
</details>

## Final Serialization

After the entire element tree is constructed, the DmnExporter serializes it to bytes:

```python
return etree.tostring(
    definitions,
    xml_declaration=True,
    encoding="UTF-8",
    pretty_print=True,
)
```

The serialization options ensure that the output is:

- **Self-describing** --- `xml_declaration=True` adds `<?xml version='1.0' encoding='UTF-8'?>` at the top
- **UTF-8 encoded** --- the standard encoding for XML interchange
- **Human-readable** --- `pretty_print=True` adds indentation and line breaks

The result is a complete, standards-compliant DMN 1.3 XML document that can be loaded into any DMN-compatible decision engine.

<!-- concept:53 -->
## XML Security Module

The **XML Security Module** (`mountainash_rules_babel/xml_security.py`) provides safe XML parsing for any future import-side operations that need to read XML files. While the DmnExporter only writes XML (using lxml's builder API, which is inherently safe), any XML reader in the system must guard against XML-based attacks.

The module configures a hardened XML parser:

```python
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB

SAFE_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    huge_tree=False,
)
```

Each setting addresses a specific attack vector:

| Setting | Value | Attack Prevented |
|---------|-------|-----------------|
| `resolve_entities` | `False` | XXE (XML External Entity) injection |
| `no_network` | `True` | Server-Side Request Forgery via DTD/entity URLs |
| `load_dtd` | `False` | DTD-based denial of service (billion laughs) |
| `huge_tree` | `False` | Memory exhaustion from deeply nested or very large documents |

The `safe_parse` function adds a file size check before parsing:

```python
def safe_parse(path: Path, max_size: int = MAX_FILE_SIZE_BYTES) -> etree._ElementTree:
    file_size = path.stat().st_size
    if file_size > max_size:
        raise ValueError(
            f"XML file {path.name} ({file_size:,} bytes) exceeds maximum "
            f"allowed size ({max_size:,} bytes)"
        )
    return etree.parse(str(path), parser=SAFE_PARSER)
```

The 50 MB size limit is a defense-in-depth measure. Even with entity resolution disabled, a very large XML file could consume excessive memory during parsing. The limit is configurable via the `max_size` parameter.

!!! warning "Always Use safe_parse for XML Input"
    Never use `etree.parse()` directly when reading external XML. The default lxml parser resolves entities and loads DTDs, which enables XXE attacks. Always use the `safe_parse` function from the XML Security Module to ensure defense against injection and denial-of-service attacks.

#### Diagram: XML Security Defense Layers

<iframe src="../../sims/xml-security-layers/main.html" width="100%" height="400px" scrolling="no"></iframe>
<details markdown="1">
<summary>XML Security Defense Layers</summary>
Type: infographic
**sim-id:** xml-security-layers<br/>
**Library:** p5.js<br/>
**Status:** Specified

**Purpose:** Illustrate the layered security defenses in the XML Security Module, showing how each setting blocks a specific attack vector.

**Components:** Concentric defense rings around a central "safe XML parse" zone. Outer ring: file size check (blocks oversized files). Next ring: no_network (blocks SSRF). Next: load_dtd=False (blocks billion laughs). Inner: resolve_entities=False (blocks XXE). Attack arrows from the outside attempt to penetrate each layer and are blocked with an X marker.

**Interactions:** Click each defense ring to see an example of the attack it prevents. Hover over blocked attacks to see the payload that would have been used. Toggle "vulnerable mode" to see what happens when defenses are removed (educational comparison, no actual execution).

**Colors:** Defense rings in graduated blues (dark outer, light inner), safe zone in green, attack arrows in crimson, block markers in gold.

**Learning Objective:** Evaluate the security implications of each XML parser setting (Bloom: Evaluate).
</details>

## Key Takeaways

- **DMN XML tree construction** uses lxml's etree builder to programmatically create well-formed, namespace-aware XML rather than string concatenation.
- The **Definitions element** is the root container, carrying the DMN namespace, a model identifier, and the human-readable decision name.
- The **Decision element** wraps a single decision point and contains one DecisionTable.
- The **DecisionTable element** sets the hit policy to UNIQUE and contains all Input, Output, and Rule elements.
- **Input elements** describe dimension columns with type references (`"number"` or `"string"`) and contain InputExpression sub-elements.
- **Output elements** declare result columns with id, label, and name attributes.
- **Rule elements** correspond to DataFrame rows, containing InputEntry elements (with FEEL expressions) and OutputEntry elements (with string values).
- The **XML Security Module** provides a hardened parser with entity resolution disabled, network access blocked, DTD loading disabled, and file size limits enforced.

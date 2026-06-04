---
title: "Chapter 7: FEEL Expression Mapping"
description: "Translation of MatchStrategy values to DMN FEEL expressions: all 11 mapping types plus NA sentinel handling."
generated_by: claude skill chapter-content-generator
date: 2026-06-03
version: 0.08
---

# Chapter 7: FEEL Expression Mapping

## Summary

This chapter covers the translation of MatchStrategy values to DMN FEEL expressions. You will learn the general FEEL Expression Mapping mechanism and each of the 11 specific mappings: exact match, not equal, range, greater than, less than, prefix, suffix, contains, set membership, set exclusion, and the NA sentinel handling for missing values.

## Concepts Covered

- FEEL Expression Mapping
- FEEL Exact Match
- FEEL Not Equal
- FEEL Range Expression
- FEEL Greater Than
- FEEL Less Than
- FEEL Prefix Match
- FEEL Suffix Match
- FEEL Contains Match
- FEEL Set Membership
- FEEL Set Exclusion
- NA Sentinel Handling

## Prerequisites

- Chapter 1: Foundations (FEEL Language, Lattice Object)
- Chapter 5: Exporter Architecture (DmnExporter Class)

---

<!-- concept:41 -->
## The Mapping Problem

Every cell in a DMN decision table's input columns must contain a FEEL expression that defines what values that cell matches. The mountainash-rules ecosystem uses a `MatchStrategy` enum internally to represent different matching behaviors (exact equality, range checking, prefix matching, etc.). The FEEL expression mapping layer translates these internal strategies into the FEEL syntax that decision engines understand.

This translation happens inside the `_feel_entry` function in `mountainash_rules_babel/exporters/dmn.py`. The function examines the dimension's match strategy and the cell value, then returns the appropriate FEEL string. Getting this mapping correct is critical: an incorrect FEEL expression will cause the decision engine to evaluate rules differently than intended.

<!-- concept:44 -->
## FEEL Expression Mapping

The **FEEL Expression Mapping** mechanism is implemented as a single dispatcher function that branches on the dimension's `match_strategy` attribute. The function signature is:

```python
def _feel_entry(value: Any, dim: Dimension) -> str:
    strategy = dim.match_strategy
    dtype = dim.data_type
    # ... dispatch logic
```

The function takes two inputs:

- **value** --- the raw cell value from the DataFrame row (could be a string, number, list, None, or NaN)
- **dim** --- the Dimension object, which carries the match strategy and data type

It returns a single string containing the FEEL expression for that cell. An empty string (`""`) means "any value matches" (a wildcard in DMN terminology).

Before dispatching on match strategy, the function first checks for NA sentinels (covered at the end of this chapter). If the value represents "no condition," the function returns an empty string immediately, regardless of the match strategy.

#### Diagram: FEEL Mapping Dispatch Flow

<iframe src="../../sims/feel-mapping-dispatch/main.html" width="100%" height="500px" scrolling="no"></iframe>
<details markdown="1">
<summary>FEEL Mapping Dispatch Flow</summary>
Type: workflow
**sim-id:** feel-mapping-dispatch<br/>
**Library:** vis-network<br/>
**Status:** Specified

**Purpose:** Show the complete dispatch logic of _feel_entry, from NA sentinel check through strategy branching to FEEL output.

**Components:** Entry node (value + dim inputs). First decision diamond: "Is NA sentinel?" If yes, output empty string. If no, branch to strategy dispatch with 11 paths (one per MatchStrategy value). Each path terminates at a FEEL output example node. Special path for RANGE shows delegation to _feel_range_entry.

**Interactions:** Click any strategy branch to see the code for that branch highlighted. Hover over FEEL output nodes to see more examples with different data types. Click "Run Example" to trace a specific value through the flow.

**Colors:** NA check in orange, strategy branches in dark slate blue, FEEL outputs in crimson, range delegation in teal.

**Learning Objective:** Trace how a given cell value and match strategy produce a specific FEEL expression (Bloom: Apply).
</details>

<!-- concept:42 -->
<!-- concept:47 -->
<!-- concept:48 -->
<!-- concept:49 -->
## FEEL Exact Match

The **FEEL exact match** is the most common mapping. It produces a FEEL expression that matches only when the input equals the specified value exactly. The output format depends on the data type:

- **String values** are quoted: `"Gold"`, `"Australia"`
- **Numeric values** are unquoted: `42`, `3.14`

The implementation handles string escaping for values that contain double quotes:

```python
if strategy == MatchStrategy.EXACT:
    if dtype == str:
        escaped = str(value).replace('"', '\\"')
        return f'"{escaped}"'
    return str(value)
```

Examples of exact match outputs:

| Input Value | Data Type | FEEL Output |
|-------------|-----------|-------------|
| `"Gold"` | str | `"Gold"` |
| `42` | int | `42` |
| `3.14` | float | `3.14` |
| `'He said "hi"'` | str | `"He said \"hi\""` |

<!-- concept:43 -->
## FEEL Not Equal

The **FEEL not equal** mapping produces a negation expression. It matches any value except the specified one. The `not()` function in FEEL is used to express exclusion:

```python
elif strategy == MatchStrategy.NOT_EQUAL:
    if dtype == str:
        escaped = str(value).replace('"', '\\"')
        return f'not("{escaped}")'
    return f"not({value})"
```

Examples:

| Input Value | Data Type | FEEL Output |
|-------------|-----------|-------------|
| `"Rejected"` | str | `not("Rejected")` |
| `0` | int | `not(0)` |

The not-equal mapping is useful for exclusion rules, such as "apply this rate to all risk categories except 'Extreme'."

## FEEL Range Expression

The **FEEL range expression** handles dimensions where a value must fall within a numeric interval. Unlike other mappings that use a single cell value, range expressions require both a minimum and a maximum. These are stored in separate DataFrame columns identified by the dimension's `range_min_field` and `range_max_field` attributes.

Because range expressions need data from multiple columns, they are handled by a separate function:

```python
def _feel_range_entry(row: dict, dim: Dimension) -> str:
    min_val = row.get(dim.range_min_field)
    max_val = row.get(dim.range_max_field)
    if min_val is None and max_val is None:
        return ""
    if min_val is None:
        return f"< {max_val}"
    if max_val is None:
        return f"> {min_val}"
    return f"[{min_val}..{max_val}]"
```

The function handles four cases:

- **Both None** --- wildcard (empty string)
- **Only max specified** --- open lower bound, translates to `< max_val`
- **Only min specified** --- open upper bound, translates to `> min_val`
- **Both specified** --- closed interval, translates to `[min..max]`

The `[min..max]` syntax in FEEL denotes an inclusive range. For the insurance example, an age range of 18 to 25 would produce `[18..25]`, meaning the rule matches any age value \( x \) where \( 18 \leq x \leq 25 \).

<!-- concept:45 -->
## FEEL Greater Than

The **FEEL greater than** mapping produces a comparison expression for values that must exceed a threshold:

```python
elif strategy == MatchStrategy.GREATER_THAN:
    return f"> {value}"
```

This produces expressions like `> 100`, `> 0`, or `> 3.14`. The FEEL specification defines this as a unary test: when evaluated against an input value \( x \), it returns true if \( x > \text{value} \).

<!-- concept:46 -->
## FEEL Less Than

The **FEEL less than** mapping is the complement of greater than:

```python
elif strategy == MatchStrategy.LESS_THAN:
    return f"< {value}"
```

It produces expressions like `< 50`, `< 1000`. Combined with greater-than rules, these enable threshold-based decision logic without requiring explicit ranges.

## FEEL Prefix Match

The **FEEL prefix match** checks whether a string input starts with a given substring. FEEL uses the `starts with` function for this:

```python
elif strategy == MatchStrategy.PREFIX:
    escaped = str(value).replace('"', '\\"')
    return f'starts with(?, "{escaped}")'
```

The `?` placeholder in the expression refers to the input value being tested. This is S-FEEL syntax for "apply this function to the input." An example output: `starts with(?, "AU")` matches any input that begins with "AU" (e.g., "Australia", "Austria", "AU-123").

## FEEL Suffix Match

The **FEEL suffix match** checks whether a string input ends with a given substring:

```python
elif strategy == MatchStrategy.SUFFIX:
    escaped = str(value).replace('"', '\\"')
    return f'ends with(?, "{escaped}")'
```

Example: `ends with(?, ".pdf")` matches any input ending with ".pdf". This is useful for file-type classification or code-based matching where the discriminating information is at the end of the value.

## FEEL Contains Match

The **FEEL contains match** checks whether a substring appears anywhere within the input:

```python
elif strategy == MatchStrategy.CONTAINS:
    escaped = str(value).replace('"', '\\"')
    return f'contains(?, "{escaped}")'
```

Example: `contains(?, "error")` matches any input containing the word "error" at any position. This is the broadest string-matching strategy and is useful for text classification rules.

The three string-matching strategies form a hierarchy of specificity:

- **Prefix** --- most restrictive (matches only at the start)
- **Suffix** --- moderate (matches only at the end)
- **Contains** --- least restrictive (matches anywhere)

#### Diagram: String Match Strategy Comparison

<iframe src="../../sims/string-match-strategies/main.html" width="100%" height="400px" scrolling="no"></iframe>
<details markdown="1">
<summary>String Match Strategy Comparison</summary>
Type: microsim
**sim-id:** string-match-strategies<br/>
**Library:** p5.js<br/>
**Status:** Specified

**Purpose:** Interactive demonstration of prefix, suffix, and contains matching against user-provided input strings.

**Components:** Input text field for the test string, three pattern input fields (prefix pattern, suffix pattern, contains pattern). Visual string with highlighted regions showing where each match occurs (green highlight for prefix at start, blue for suffix at end, orange for contains in middle). Match/no-match indicator for each strategy.

**Interactions:** Type in the test string field to see real-time matching results. Change pattern values to experiment with different matching criteria. Toggle "show FEEL expression" to see the generated FEEL output for each active pattern.

**Controls:** Text input for test string, three text inputs for patterns, toggle for FEEL expression display, reset button.

**Colors:** Prefix match highlight in dark green, suffix in dark blue, contains in orange, no-match indicator in gray.

**Learning Objective:** Apply string-matching strategies to predict which values will match a given pattern (Bloom: Apply).
</details>

<!-- concept:50 -->
## FEEL Set Membership

The **FEEL set membership** mapping checks whether the input value is one of a specified set of values. The FEEL representation is a comma-separated list of quoted strings:

```python
elif strategy == MatchStrategy.SET_MEMBERSHIP:
    items = value if isinstance(value, list) else [value]
    if not items:
        return ""
    parts = [f'"{str(i).replace(chr(34), chr(92)+chr(34))}"' for i in items]
    return ", ".join(parts)
```

The value can be either a single item or a list. If it is a single item, it is wrapped in a list for uniform processing. Each item is quoted and escaped, then joined with commas.

Example: for a value `["Gold", "Platinum"]`, the output is `"Gold", "Platinum"`. In FEEL semantics, this is a disjunction: the rule matches if the input equals "Gold" OR "Platinum".

<!-- concept:51 -->
## FEEL Set Exclusion

The **FEEL set exclusion** mapping is the negation of set membership. It matches any value that is NOT in the specified set:

```python
elif strategy == MatchStrategy.SET_EXCLUSION:
    items = value if isinstance(value, list) else [value]
    if not items:
        return ""
    parts = [f'"{str(i).replace(chr(34), chr(92)+chr(34))}"' for i in items]
    return f'not({", ".join(parts)})'
```

Example: for a value `["Rejected", "Expired"]`, the output is `not("Rejected", "Expired")`. The rule matches any input that is neither "Rejected" nor "Expired".

Set membership and set exclusion together enable partitioning of categorical values:

| Strategy | Values | Matches |
|----------|--------|---------|
| SET_MEMBERSHIP | `["Gold", "Platinum"]` | Gold or Platinum only |
| SET_EXCLUSION | `["Gold", "Platinum"]` | Everything except Gold and Platinum |

<!-- concept:52 -->
## NA Sentinel Handling

**NA sentinel handling** addresses the question: how does babel represent "no condition" (a wildcard) in a cell? Different data sources use different conventions for missing or inapplicable values. The `_feel_entry` function recognizes four sentinel patterns and maps all of them to an empty FEEL string (wildcard):

```python
# Handle null/NA sentinels -> empty FEEL (any match)
if value is None:
    return ""
if isinstance(value, float) and value != value:  # NaN
    return ""
if isinstance(value, (int, float)) and not isinstance(value, bool) and value == -999999999:
    return ""
if isinstance(value, str) and value == "<NA>":
    return ""
```

The four recognized sentinels are:

1. **Python None** --- the standard null value
2. **NaN (Not a Number)** --- detected via the `value != value` trick (NaN is the only float that is not equal to itself)
3. **-999999999** --- a numeric sentinel commonly used in legacy systems where null is not supported
4. **The string `"<NA>"`** --- an explicit textual marker for missing values

All four produce an empty string in the FEEL output, which DMN engines interpret as "this condition is not checked; any input value satisfies this cell."

This sentinel detection runs before the match strategy dispatch, so it applies universally regardless of which strategy the dimension uses. If a cell contains a sentinel value, it becomes a wildcard regardless of whether the dimension normally uses exact matching, range checking, or any other strategy.

!!! tip "Choosing Sentinel Values in Source Data"
    When preparing CSV data for babel, use empty cells (which Polars reads as `None`) for wildcard conditions. Avoid using `-999999999` or `"<NA>"` in new data --- these are supported for backward compatibility with legacy systems, but `None`/empty is the preferred convention.

## Complete Mapping Reference

The following table summarizes all FEEL expression mappings for quick reference. Each row shows the MatchStrategy, the FEEL output format, and a concrete example:

| Match Strategy | FEEL Pattern | Example (str) | Example (num) |
|---------------|-------------|---------------|---------------|
| EXACT | `"value"` / `value` | `"Gold"` | `42` |
| NOT_EQUAL | `not("value")` / `not(value)` | `not("Rejected")` | `not(0)` |
| RANGE | `[min..max]` | N/A | `[18..25]` |
| GREATER_THAN | `> value` | N/A | `> 100` |
| LESS_THAN | `< value` | N/A | `< 50` |
| PREFIX | `starts with(?, "val")` | `starts with(?, "AU")` | N/A |
| SUFFIX | `ends with(?, "val")` | `ends with(?, ".pdf")` | N/A |
| CONTAINS | `contains(?, "val")` | `contains(?, "error")` | N/A |
| SET_MEMBERSHIP | `"a", "b", "c"` | `"Gold", "Platinum"` | N/A |
| SET_EXCLUSION | `not("a", "b")` | `not("Rejected", "Expired")` | N/A |
| Any (NA sentinel) | (empty string) | (empty) | (empty) |

#### Diagram: FEEL Expression Interactive Builder

<iframe src="../../sims/feel-expression-builder/main.html" width="100%" height="500px" scrolling="no"></iframe>
<details markdown="1">
<summary>FEEL Expression Interactive Builder</summary>
Type: microsim
**sim-id:** feel-expression-builder<br/>
**Library:** p5.js<br/>
**Status:** Specified

**Purpose:** Allow users to select a match strategy, enter a value, and see the resulting FEEL expression generated in real-time.

**Components:** Dropdown selector for MatchStrategy (11 options). Text input for value (or min/max for RANGE). Data type toggle (string/number). Output panel showing the generated FEEL expression with syntax highlighting. "Test" panel where users can enter a test input and see whether it would match.

**Controls:** MatchStrategy dropdown, value text input, data type radio buttons, "Generate" button, test input field, "Test Match" button.

**Interactions:** Changing any input parameter immediately updates the generated FEEL expression. The test panel evaluates whether a given input value would satisfy the FEEL expression (using JavaScript approximation of FEEL semantics). Invalid combinations (e.g., PREFIX with numeric type) show a warning.

**Colors:** Generated expression in dark blue monospace, match result in green (match) or crimson (no match), warning messages in orange.

**Learning Objective:** Create correct FEEL expressions by selecting appropriate match strategies and values (Bloom: Create).
</details>

## Key Takeaways

- **FEEL Expression Mapping** is a dispatcher function that translates MatchStrategy + cell value pairs into FEEL syntax strings.
- **FEEL Exact Match** produces quoted strings or unquoted numbers depending on the data type.
- **FEEL Not Equal** wraps the value in a `not()` function call.
- **FEEL Range Expression** uses `[min..max]` notation and handles open-ended ranges with `<` or `>` syntax.
- **FEEL Greater Than** and **FEEL Less Than** produce simple comparison operators (`> value`, `< value`).
- **FEEL Prefix**, **Suffix**, and **Contains** use FEEL's built-in string functions (`starts with`, `ends with`, `contains`) with the `?` input placeholder.
- **FEEL Set Membership** produces a comma-separated list of quoted values (disjunction).
- **FEEL Set Exclusion** wraps the set in a `not()` call (negated disjunction).
- **NA Sentinel Handling** recognizes four sentinel patterns (None, NaN, -999999999, "<NA>") and maps them all to an empty FEEL string (wildcard).

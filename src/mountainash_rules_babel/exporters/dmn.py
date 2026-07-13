from __future__ import annotations

import typing as t
from pathlib import Path

from lxml import etree

from mountainash_rules import DataType, Dimension, HitPolicy, Lattice, MatchStrategy

from mountainash_rules_babel.errors import SchemaContractError
from mountainash_rules_babel.exporters.base import resolve_lattice

DMN_NS = "https://www.omg.org/spec/DMN/20191111/MODEL/"
NSMAP = {None: DMN_NS}

_DMN_POLICY = {
    HitPolicy.COLLECT: "COLLECT",
    HitPolicy.UNIQUE: "UNIQUE",
    HitPolicy.FIRST: "FIRST",
    HitPolicy.PRIORITY: "PRIORITY",
    HitPolicy.ANY: "ANY",
    HitPolicy.RULE_ORDER: "RULE ORDER",
}


def _type_ref(data_type: DataType) -> str:
    if data_type.is_numeric:
        return "number"
    if data_type is DataType.BOOL:
        return "boolean"
    if data_type.is_temporal:
        return "date"
    return "string"


def _feel_entry(value: t.Any, dim: Dimension) -> str:
    """Map a cell value + dimension metadata to a FEEL expression string."""
    strategy = dim.match_strategy
    dtype = dim.data_type

    # Handle null/NA sentinels → empty FEEL (any match)
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    # Numeric sentinel
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == -999999999:
        return ""
    # String sentinel
    if isinstance(value, str) and value == "<NA>":
        return ""

    if strategy == MatchStrategy.EXACT:
        if dtype is DataType.STR:
            escaped = str(value).replace('"', '\\"')
            return f'"{escaped}"'
        return str(value)

    elif strategy == MatchStrategy.NOT_EQUAL:
        if dtype is DataType.STR:
            escaped = str(value).replace('"', '\\"')
            return f'not("{escaped}")'
        return f"not({value})"

    elif strategy == MatchStrategy.RANGE:
        # value is the min; we need max from sibling — handled at row level
        # This branch shouldn't be called directly; see _feel_range
        return str(value)

    elif strategy == MatchStrategy.GREATER_THAN:
        return f"> {value}"

    elif strategy == MatchStrategy.LESS_THAN:
        return f"< {value}"

    elif strategy == MatchStrategy.PREFIX:
        escaped = str(value).replace('"', '\\"')
        return f'starts with(?, "{escaped}")'

    elif strategy == MatchStrategy.SUFFIX:
        escaped = str(value).replace('"', '\\"')
        return f'ends with(?, "{escaped}")'

    elif strategy == MatchStrategy.CONTAINS:
        escaped = str(value).replace('"', '\\"')
        return f'contains(?, "{escaped}")'

    elif strategy == MatchStrategy.SET_MEMBERSHIP:
        items = value if isinstance(value, list) else [value]
        if not items:
            return ""
        parts = [f'"{str(i).replace(chr(34), chr(92)+chr(34))}"' for i in items]
        return ", ".join(parts)

    elif strategy == MatchStrategy.SET_EXCLUSION:
        items = value if isinstance(value, list) else [value]
        if not items:
            return ""
        parts = [f'"{str(i).replace(chr(34), chr(92)+chr(34))}"' for i in items]
        return f'not({", ".join(parts)})'

    elif strategy == MatchStrategy.REGEX:
        # FEEL S-FEEL doesn't support regex natively; emit as plain string
        return str(value)

    return str(value)


def _feel_range_entry(row: dict, dim: Dimension) -> str:
    """Build a FEEL range expression from min/max columns."""
    min_val = row.get(dim.range_min_field)
    max_val = row.get(dim.range_max_field)
    if min_val is None and max_val is None:
        return ""
    if min_val is None:
        return f"< {max_val}"
    if max_val is None:
        return f"> {min_val}"
    return f"[{min_val}..{max_val}]"


class DmnExporter:
    name: str = "dmn"
    file_extension: str = ".dmn"

    def export(self, lattice: Lattice, path: Path, **options) -> Path:
        path = Path(path)
        data = self.export_bytes(lattice, **options)
        path.write_bytes(data)
        return path

    def export_bytes(
        self,
        lattice: Lattice,
        *,
        include_tracking: bool = False,
        assume_unique: bool = False,
        **options,
    ) -> bytes:
        decision_name = options.get("decision_name", "GeneratedDecision")
        table_name = options.get("table_name", "GeneratedTable")

        view = resolve_lattice(lattice, include_tracking=include_tracking)
        policy = lattice.metadata.hit_policy
        if view.is_composed and policy == HitPolicy.UNIQUE and not assume_unique:
            raise SchemaContractError(
                "hit_policy=unique is unproven for a composed lattice "
                "(distinct maximal combinations can overlap); run a "
                "conflicts analysis and pass assume_unique=True to override"
            )

        df = view.df
        output_cols = view.output_columns

        # Build XML tree
        definitions = etree.Element("definitions", nsmap=NSMAP)
        definitions.set("id", "definitions_babel")
        definitions.set("name", decision_name)
        definitions.set("namespace", "https://mountainash.io/babel")

        decision = etree.SubElement(definitions, f"{{{DMN_NS}}}decision")
        decision.set("id", f"decision_{table_name}")
        decision.set("name", decision_name)

        dt = etree.SubElement(decision, f"{{{DMN_NS}}}decisionTable")
        dt.set("id", f"dt_{table_name}")
        dt.set("hitPolicy", _DMN_POLICY[policy])

        # Input elements (one per dimension)
        for dim in lattice.metadata.dimensions:
            inp = etree.SubElement(dt, f"{{{DMN_NS}}}input")
            inp.set("id", f"input_{dim.dimension_name}")
            inp.set("label", dim.dimension_name)

            inp_expr = etree.SubElement(inp, f"{{{DMN_NS}}}inputExpression")
            inp_expr.set("id", f"inputExpr_{dim.dimension_name}")
            inp_expr.set("typeRef", _type_ref(dim.data_type))

            text_el = etree.SubElement(inp_expr, f"{{{DMN_NS}}}text")
            text_el.text = dim.dimension_name

        # Output elements
        for col in output_cols:
            out = etree.SubElement(dt, f"{{{DMN_NS}}}output")
            out.set("id", f"output_{col}")
            out.set("label", col)
            out.set("name", col)

        # Rules (one per row)
        rows = df.to_dicts()
        tracking_rows = (
            view.tracking.to_dicts() if view.tracking is not None else None
        )
        for row_idx, row in enumerate(rows):
            rule_el = etree.SubElement(dt, f"{{{DMN_NS}}}rule")
            rule_el.set("id", f"rule_{row_idx}")
            if tracking_rows is not None:
                desc = etree.SubElement(rule_el, f"{{{DMN_NS}}}description")
                desc.text = (
                    f"prime_product={tracking_rows[row_idx]['__prime_product']}"
                )

            # Input entries (view.df carries resolved flat names)
            for dim in lattice.metadata.dimensions:
                ie = etree.SubElement(rule_el, f"{{{DMN_NS}}}inputEntry")
                ie.set("id", f"ie_{row_idx}_{dim.dimension_name}")
                text_el = etree.SubElement(ie, f"{{{DMN_NS}}}text")

                if dim.match_strategy == MatchStrategy.RANGE:
                    text_el.text = _feel_range_entry(row, dim)
                else:
                    value = row.get(dim.resolved_rule_field)
                    text_el.text = _feel_entry(value, dim)

            # Output entries
            for col in output_cols:
                oe = etree.SubElement(rule_el, f"{{{DMN_NS}}}outputEntry")
                oe.set("id", f"oe_{row_idx}_{col}")
                text_el = etree.SubElement(oe, f"{{{DMN_NS}}}text")
                val = row.get(col)
                text_el.text = "" if val is None else str(val)

        return etree.tostring(
            definitions,
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=True,
        )

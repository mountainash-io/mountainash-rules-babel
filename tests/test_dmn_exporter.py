import tempfile
from pathlib import Path

import polars as pl
from lxml import etree
from mountainash_rules.aggregate import Aggregate
from mountainash_rules.constants import MatchStrategy
from mountainash_rules.dimension import Dimension, DimensionsMetadata
from mountainash_rules.lattice import Lattice

from mountainash_rules_babel.exporters.dmn import DmnExporter

DMN_NS = "https://www.omg.org/spec/DMN/20191111/MODEL/"


def _make_lattice() -> Lattice:
    metadata = DimensionsMetadata(
        dimensions=[
            Dimension(dimension_name="country", match_strategy=MatchStrategy.EXACT, data_type=str),
            Dimension(dimension_name="tier", match_strategy=MatchStrategy.EXACT, data_type=str),
        ]
    )
    df = pl.DataFrame({
        "country": ["AU", "NZ", "AU"],
        "tier": ["gold", "gold", "silver"],
        "discount": [0.2, 0.15, 0.1],
    })
    return Lattice(
        dataframe=df,
        metadata=metadata,
        aggregates=[Aggregate(column_name="discount", operation="sum")],
        partition_key=None,
    )


def test_dmn_export_produces_valid_xml():
    exporter = DmnExporter()
    lattice = _make_lattice()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "pricing.dmn"
        result = exporter.export(lattice, out_path)
        assert result.exists()

        tree = etree.parse(str(out_path))
        root = tree.getroot()
        assert root.tag == f"{{{DMN_NS}}}definitions"


def test_dmn_export_has_correct_row_count():
    exporter = DmnExporter()
    lattice = _make_lattice()
    data = exporter.export_bytes(lattice)
    tree = etree.fromstring(data)

    ns = {"dmn": DMN_NS}
    rules = tree.findall(".//dmn:rule", ns)
    assert len(rules) == 3


def test_dmn_export_has_input_and_output_columns():
    exporter = DmnExporter()
    lattice = _make_lattice()
    data = exporter.export_bytes(lattice)
    tree = etree.fromstring(data)

    ns = {"dmn": DMN_NS}
    inputs = tree.findall(".//dmn:input", ns)
    outputs = tree.findall(".//dmn:output", ns)
    assert len(inputs) == 2  # country, tier
    assert len(outputs) == 1  # discount


def test_dmn_export_feel_values_are_quoted_strings():
    exporter = DmnExporter()
    lattice = _make_lattice()
    data = exporter.export_bytes(lattice)
    tree = etree.fromstring(data)

    ns = {"dmn": DMN_NS}
    first_rule = tree.findall(".//dmn:rule", ns)[0]
    input_entries = first_rule.findall("dmn:inputEntry/dmn:text", ns)
    # EXACT string values should be quoted in FEEL
    assert input_entries[0].text == '"AU"'
    assert input_entries[1].text == '"gold"'


def test_dmn_exporter_protocol_fields():
    exporter = DmnExporter()
    assert exporter.name == "dmn"
    assert exporter.file_extension == ".dmn"

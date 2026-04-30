import tempfile
from pathlib import Path

import pytest

from mountainash_rules_babel.xml_security import safe_parse, MAX_FILE_SIZE_BYTES


def test_safe_parse_valid_xml():
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
        f.write('<?xml version="1.0"?><root><child>text</child></root>')
        f.flush()
        tree = safe_parse(Path(f.name))
    assert tree.getroot().tag == "root"


def test_safe_parse_rejects_xxe():
    xxe_xml = '<?xml version="1.0"?>\n<!DOCTYPE foo [\n  <!ENTITY xxe SYSTEM "file:///etc/passwd">\n]>\n<root>&xxe;</root>'
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
        f.write(xxe_xml)
        f.flush()
        tree = safe_parse(Path(f.name))
    root = tree.getroot()
    # With resolve_entities=False, the entity reference is not expanded
    assert root.text is None or "/root:" not in (root.text or "")


def test_safe_parse_rejects_oversized_file():
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="wb", delete=False) as f:
        f.write(b'<?xml version="1.0"?><root>')
        f.write(b"x" * (1024 + 1))  # Use a small limit for testing
        f.write(b"</root>")
        f.flush()
        with pytest.raises(ValueError, match="exceeds maximum"):
            safe_parse(Path(f.name), max_size=1024)

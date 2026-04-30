from __future__ import annotations

from pathlib import Path

from lxml import etree

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB

SAFE_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    huge_tree=False,
)


def safe_parse(
    path: Path,
    max_size: int = MAX_FILE_SIZE_BYTES,
) -> etree._ElementTree:
    file_size = path.stat().st_size
    if file_size > max_size:
        raise ValueError(
            f"XML file {path.name} ({file_size:,} bytes) exceeds maximum "
            f"allowed size ({max_size:,} bytes)"
        )
    return etree.parse(str(path), parser=SAFE_PARSER)

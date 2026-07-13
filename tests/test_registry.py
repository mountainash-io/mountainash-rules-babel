from pathlib import Path

import pytest
from mountainash_rules import Lattice

from mountainash_rules_babel.errors import FormatNotFoundError
from mountainash_rules_babel.registry import PluginRegistry


# Lightweight fakes (mirror the ones in test_protocols.py)
class FakeExporter:
    name = "fake"
    file_extension = ".fake"

    def export(self, lattice: Lattice, path: Path, **options) -> Path:
        path.write_text("fake")
        return path

    def export_bytes(self, lattice: Lattice, **options) -> bytes:
        return b"fake"


class FakeImporter:
    name = "fake"
    file_extensions = [".fake"]

    def import_lattice(self, path: Path, **options) -> Lattice:
        raise NotImplementedError

class FakeValidator:
    name = "fake"

    def validate(self, lattice: Lattice, **options):
        return None


def test_register_and_get_exporter():
    reg = PluginRegistry(auto_discover=False)
    reg.register_exporter(FakeExporter())
    exp = reg.get_exporter("fake")
    assert exp.name == "fake"


def test_register_and_get_importer():
    reg = PluginRegistry(auto_discover=False)
    reg.register_importer(FakeImporter())
    imp = reg.get_importer("fake")
    assert imp.name == "fake"


def test_register_and_get_validator():
    reg = PluginRegistry(auto_discover=False)
    reg.register_validator(FakeValidator())
    val = reg.get_validator("fake")
    assert val.name == "fake"


def test_get_unknown_exporter_raises():
    reg = PluginRegistry(auto_discover=False)
    reg.register_exporter(FakeExporter())
    with pytest.raises(FormatNotFoundError) as exc_info:
        reg.get_exporter("nope")
    assert "nope" in str(exc_info.value)
    assert "fake" in str(exc_info.value)


def test_list_exporters():
    reg = PluginRegistry(auto_discover=False)
    reg.register_exporter(FakeExporter())
    assert reg.list_exporters() == ["fake"]


def test_list_importers_empty():
    reg = PluginRegistry(auto_discover=False)
    assert reg.list_importers() == []


def test_infer_importer_from_extension():
    reg = PluginRegistry(auto_discover=False)
    reg.register_importer(FakeImporter())
    imp = reg.get_importer_for_extension(".fake")
    assert imp.name == "fake"


def test_infer_importer_unknown_extension():
    reg = PluginRegistry(auto_discover=False)
    with pytest.raises(FormatNotFoundError):
        reg.get_importer_for_extension(".xyz")


def test_auto_discover_does_not_crash():
    reg = PluginRegistry(auto_discover=True)
    assert isinstance(reg.list_exporters(), list)

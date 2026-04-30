from __future__ import annotations

import importlib.metadata
import logging
import typing as t

from mountainash_rules_babel.decomposers.base import Decomposer
from mountainash_rules_babel.errors import FormatNotFoundError
from mountainash_rules_babel.exporters.base import Exporter
from mountainash_rules_babel.importers.base import Importer
from mountainash_rules_babel.validators.base import Validator

logger = logging.getLogger(__name__)

_ENTRY_POINT_GROUPS: dict[str, str] = {
    "exporter": "mountainash_babel.exporters",
    "importer": "mountainash_babel.importers",
    "decomposer": "mountainash_babel.decomposers",
    "validator": "mountainash_babel.validators",
}


class PluginRegistry:
    def __init__(self, auto_discover: bool = True) -> None:
        self._exporters: dict[str, Exporter] = {}
        self._importers: dict[str, Importer] = {}
        self._decomposers: dict[str, Decomposer] = {}
        self._validators: dict[str, Validator] = {}
        if auto_discover:
            self.discover()

    def discover(self) -> None:
        for category, group in _ENTRY_POINT_GROUPS.items():
            for ep in importlib.metadata.entry_points(group=group):
                try:
                    cls = ep.load()
                    instance = cls()
                    if category == "exporter":
                        self._exporters[ep.name] = instance
                    elif category == "importer":
                        self._importers[ep.name] = instance
                    elif category == "decomposer":
                        self._decomposers[ep.name] = instance
                    elif category == "validator":
                        self._validators[ep.name] = instance
                except Exception as exc:
                    logger.debug("Failed to load %s plugin '%s': %s", category, ep.name, exc)

    def register_exporter(self, exporter: Exporter) -> None:
        self._exporters[exporter.name] = exporter

    def register_importer(self, importer: Importer) -> None:
        self._importers[importer.name] = importer

    def register_decomposer(self, decomposer: Decomposer) -> None:
        self._decomposers[decomposer.name] = decomposer

    def register_validator(self, validator: Validator) -> None:
        self._validators[validator.name] = validator

    def get_exporter(self, name: str) -> Exporter:
        if name not in self._exporters:
            raise FormatNotFoundError(name, available=list(self._exporters.keys()))
        return self._exporters[name]

    def get_importer(self, name: str) -> Importer:
        if name not in self._importers:
            raise FormatNotFoundError(name, available=list(self._importers.keys()))
        return self._importers[name]

    def get_decomposer(self, name: str) -> Decomposer:
        if name not in self._decomposers:
            raise FormatNotFoundError(name, available=list(self._decomposers.keys()))
        return self._decomposers[name]

    def get_validator(self, name: str) -> Validator:
        if name not in self._validators:
            raise FormatNotFoundError(name, available=list(self._validators.keys()))
        return self._validators[name]

    def get_importer_for_extension(self, ext: str) -> Importer:
        for imp in self._importers.values():
            if ext in imp.file_extensions:
                return imp
        available: list[str] = []
        for imp in self._importers.values():
            available.extend(imp.file_extensions)
        raise FormatNotFoundError(ext, available=available)

    def list_exporters(self) -> list[str]:
        return sorted(self._exporters.keys())

    def list_importers(self) -> list[str]:
        return sorted(self._importers.keys())

    def list_decomposers(self) -> list[str]:
        return sorted(self._decomposers.keys())

    def list_validators(self) -> list[str]:
        return sorted(self._validators.keys())


registry = PluginRegistry(auto_discover=True)

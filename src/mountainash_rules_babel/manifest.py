"""LatticeManifest: the sidecar babel ships alongside exported rule tables."""

from __future__ import annotations

import pathlib
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from mountainash_rules import DimensionsMetadata, Lattice


class AggregateSpec(BaseModel):
    column_name: str
    operation: str = "sum"


class LatticeManifest(BaseModel):
    """Flat CSV sidecar metadata for inspection-only lattice values."""

    model_config = ConfigDict(extra="forbid")

    fidelity: Literal["flat_values"] = "flat_values"
    dimensions: DimensionsMetadata
    aggregates: list[AggregateSpec] = Field(default_factory=list)

    @classmethod
    def for_lattice(cls, lattice: Lattice) -> "LatticeManifest":
        return cls(
            dimensions=lattice.metadata,
            aggregates=[
                AggregateSpec(column_name=a.column_name, operation=a.operation)
                for a in lattice.aggregates
            ],
        )

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            self.model_dump(mode="json"),
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, text: str) -> "LatticeManifest":
        return cls.model_validate(yaml.safe_load(text))

    def to_yaml_file(self, path: str | pathlib.Path) -> pathlib.Path:
        path = pathlib.Path(path)
        path.write_text(self.to_yaml(), encoding="utf-8")
        return path

    @classmethod
    def from_yaml_file(cls, path: str | pathlib.Path) -> "LatticeManifest":
        return cls.from_yaml(pathlib.Path(path).read_text(encoding="utf-8"))

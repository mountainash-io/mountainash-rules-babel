"""LatticeManifest: the sidecar babel ships alongside exported rule tables."""

from __future__ import annotations

import pathlib

import yaml
from pydantic import BaseModel, Field

from mountainash_rules.dimension import DimensionsMetadata
from mountainash_rules.lattice import Lattice


class AggregateSpec(BaseModel):
    column_name: str
    operation: str = "sum"


class LatticeManifest(BaseModel):
    """Everything needed to rehydrate an exported table: dimensions
    (embedding the engine's DimensionsMetadata payload, hit_policy
    included) plus aggregate declarations."""

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
            self.model_dump(mode="json", exclude_defaults=True),
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

"""Catálogo de componentes empacotado em `app/catalogs/components.json`."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal[
    "structure",
    "avionics",
    "propulsion_engine",
    "propulsion_tank",
    "power_solar",
    "power_battery",
    "comms",
    "attitude",
    "payload",
    "thermal",
]


class Component(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    category: Category
    mass_kg: float = Field(gt=0)
    dimensions_m: tuple[float, float, float]
    power_consumption_w: float = Field(ge=0)
    power_generation_w: float = Field(ge=0)
    cost_musd: float = Field(ge=0)
    reliability: float = Field(gt=0, le=1)
    fictional: bool
    source: str
    params: dict[str, Any] = Field(default_factory=dict)


class Catalog(BaseModel):
    version: str
    notice: str
    components: list[Component]

    def by_id(self) -> dict[str, Component]:
        return {c.id: c for c in self.components}


DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalogs" / "components.json"


@lru_cache(maxsize=4)
def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> Catalog:
    with path.open(encoding="utf-8") as fh:
        catalog = Catalog.model_validate(json.load(fh))
    ids = [c.id for c in catalog.components]
    if len(ids) != len(set(ids)):
        raise ValueError("IDs duplicados no catálogo de componentes.")
    return catalog

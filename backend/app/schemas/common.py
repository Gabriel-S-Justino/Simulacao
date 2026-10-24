"""Metadados comuns de procedência (subconjunto do contrato 4.9)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Provenance(BaseModel):
    source: str
    kind: Literal["calculated", "observed", "approximation", "synthetic"]
    computed_at: datetime
    simulator_version: str
    model: str
    reference_frame: str
    units: dict[str, str]
    assumptions: list[str]

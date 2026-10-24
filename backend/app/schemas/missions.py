import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.flight import (
    BurnIn,
    CircularOrbitIn,
    Feasibility,
    IntegratorIn,
    ObjectiveIn,
    OrbitOut,
    SimulateOut,
)
from app.schemas.spacecraft import DesignIn, DesignReportOut

MAX_DURATION_S = 30 * 86_400


class ProjectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    mission_count: int


class MissionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    design: DesignIn
    initial_orbit: CircularOrbitIn
    objective: ObjectiveIn | None = None
    burns: list[BurnIn] = Field(default_factory=list, max_length=32)
    duration_s: float = Field(default=86_400, gt=0, le=MAX_DURATION_S)
    seed: int = Field(default=0, ge=0, le=2**31 - 1)
    integrator: IntegratorIn = Field(default_factory=IntegratorIn)


class MissionPatch(BaseModel):
    """Alterar o plano invalida checkpoints e relatórios anteriores (são removidos)."""

    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    design: DesignIn | None = None
    initial_orbit: CircularOrbitIn | None = None
    objective: ObjectiveIn | None = None
    burns: list[BurnIn] | None = Field(default=None, max_length=32)
    duration_s: float | None = Field(default=None, gt=0, le=MAX_DURATION_S)
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    integrator: IntegratorIn | None = None


class MissionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    status: Literal["draft", "simulated"]
    design: DesignIn
    initial_orbit: CircularOrbitIn
    objective: ObjectiveIn | None
    burns: list[BurnIn]
    duration_s: float
    physics: dict[str, object]
    seed: int
    simulator_version: str
    created_at: datetime
    updated_at: datetime
    checkpoint_count: int
    run_count: int


class MissionValidationOut(BaseModel):
    design: DesignReportOut
    feasibility: Feasibility
    valid: bool


class PlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["hohmann"] = "hohmann"
    start_time_s: float = Field(default=600.0, ge=0, le=86_400)


class RunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n_samples: int = Field(default=1500, ge=16, le=6000)


class StageStateOut(BaseModel):
    name: str
    burnable_kg: float
    isp_s: float | None
    thrust_n: float
    jettison_mass_kg: float


class StateOut(BaseModel):
    source: Literal["initial", "checkpoint"]
    t_s: float
    position_m: tuple[float, float, float]
    velocity_ms: tuple[float, float, float]
    mass_kg: float
    stages: list[StageStateOut]
    orbit: OrbitOut | None


class CheckpointIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    t_s: float = Field(ge=0, le=MAX_DURATION_S)
    label: str = Field(default="", max_length=64)


class CheckpointOut(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID
    label: str
    t_s: float
    state: StateOut
    simulator_version: str
    created_at: datetime


class RunSummaryOut(BaseModel):
    id: uuid.UUID
    from_checkpoint_id: uuid.UUID | None
    simulator_version: str
    created_at: datetime
    summary: dict[str, object]


class MissionRunOut(BaseModel):
    run_id: uuid.UUID
    from_checkpoint_id: uuid.UUID | None
    simulation: SimulateOut

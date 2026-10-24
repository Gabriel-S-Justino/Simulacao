from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Provenance
from app.schemas.spacecraft import DesignIn, DesignReportOut


class CircularOrbitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    altitude_m: float = Field(ge=150_000, le=400_000_000)
    inclination_deg: float = Field(default=0.0, ge=0, le=180)


class HohmannIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    initial_altitude_m: float = Field(ge=150_000, le=400_000_000)
    target_altitude_m: float = Field(ge=150_000, le=400_000_000)
    start_time_s: float = Field(default=600.0, ge=0, le=86_400)
    design: DesignIn | None = None


class BurnIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    t_s: float = Field(ge=0)
    dv_vnb_ms: tuple[float, float, float]
    label: str = Field(default="", max_length=64)


class BurnOut(BurnIn):
    pass


class Feasibility(BaseModel):
    available_delta_v_ms: float
    required_delta_v_ms: float
    margin_ms: float
    feasible: bool


class HohmannOut(BaseModel):
    dv1_ms: float
    dv2_ms: float
    total_delta_v_ms: float
    transfer_time_s: float
    transfer_semi_major_axis_m: float
    burns: list[BurnOut]
    suggested_duration_s: float
    feasibility: Feasibility | None
    provenance: Provenance


class IntegratorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rtol: float = Field(default=1e-11, ge=1e-13, le=1e-6)


class ObjectiveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["circular_orbit"] = "circular_orbit"
    target_altitude_m: float = Field(ge=150_000, le=400_000_000)
    tolerance_m: float = Field(default=10_000, gt=0, le=1_000_000)


class SimulateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    design: DesignIn
    initial_orbit: CircularOrbitIn
    burns: list[BurnIn] = Field(default_factory=list, max_length=32)
    duration_s: float = Field(gt=0, le=30 * 86_400)
    n_samples: int = Field(default=1500, ge=16, le=6000)
    objective: ObjectiveIn | None = None
    integrator: IntegratorIn = Field(default_factory=IntegratorIn)


class OrbitOut(BaseModel):
    orbit_type: str
    semi_major_axis_m: float
    eccentricity: float
    inclination_deg: float
    periapsis_altitude_m: float
    apoapsis_altitude_m: float | None
    period_s: float | None
    specific_energy_jkg: float
    specific_angular_momentum_m2s: float


class SimEventOut(BaseModel):
    t_s: float
    kind: str
    message: str
    data: dict[str, float]


class ObjectiveOut(BaseModel):
    achieved: bool
    periapsis_error_m: float | None
    apoapsis_error_m: float | None
    tolerance_m: float


class Diagnostics(BaseModel):
    integrator: str
    rtol: float
    atol_position_m: float
    atol_velocity_ms: float
    function_evaluations: int
    max_rel_energy_drift: float
    max_rel_angular_momentum_drift: float
    compute_time_ms: float


class Trajectory(BaseModel):
    t_s: list[float]
    position_m: list[tuple[float, float, float]]
    velocity_ms: list[tuple[float, float, float]]
    mass_kg: list[float]


class SimulateOut(BaseModel):
    design: DesignReportOut
    initial_orbit: OrbitOut
    final_orbit: OrbitOut | None
    trajectory: Trajectory
    events: list[SimEventOut]
    delta_v_executed_ms: float
    propellant_used_kg: float
    final_mass_kg: float
    terminated_early: bool
    objective: ObjectiveOut | None
    diagnostics: Diagnostics
    provenance: Provenance

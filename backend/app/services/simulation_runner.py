"""Execução de simulações e montagem das respostas da API (compartilhado por rotas e missões)."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from app.core.version import SIMULATOR_VERSION
from app.domain.constants import MU_EARTH, R_EARTH_EQ
from app.domain.orbital_mechanics.elements import OrbitSummary
from app.domain.spacecraft.catalog import load_catalog
from app.domain.spacecraft.design import DesignReport, evaluate_design
from app.schemas.common import Provenance
from app.schemas.flight import (
    BurnIn,
    CircularOrbitIn,
    Diagnostics,
    ObjectiveIn,
    ObjectiveOut,
    OrbitOut,
    SimEventOut,
    SimulateOut,
    Trajectory,
)
from app.schemas.spacecraft import DesignIn, DesignReportOut
from app.services.flight import (
    build_stack,
    circular_orbit_state,
    evaluate_circular_target,
    summarize_earth,
)
from app.simulation.propagator import (
    Burn,
    IntegratorSettings,
    SimResult,
    StageTank,
    propagate,
)

FRAME = "ECI inercial centrado na Terra (eixos tipo J2000; rotação da Terra não modelada)"
SI_UNITS = {"length": "m", "time": "s", "velocity": "m/s", "mass": "kg"}
INTEGRATOR_NAME = "DOP853 (Runge-Kutta 8(5,3), passo adaptativo)"
SIM_ASSUMPTIONS = [
    "Terra como massa pontual (sem J2, arrasto ou terceiros corpos)",
    "Queimas impulsivas; duração finita estimada e sinalizada",
    "Órbita inicial circular com RAAN = 0 e argumento de latitude = 0",
]


@dataclass(frozen=True, slots=True)
class StartState:
    """Estado de partida de uma retomada (checkpoint)."""

    t_s: float
    r: np.ndarray
    v: np.ndarray
    stages: list[StageTank]


def design_report(design: DesignIn) -> DesignReport:
    return evaluate_design(design.to_domain(), load_catalog().by_id())


def run_simulation(
    design: DesignIn,
    initial_orbit: CircularOrbitIn,
    burns: list[BurnIn],
    duration_s: float,
    n_samples: int,
    objective: ObjectiveIn | None,
    rtol: float,
    start: StartState | None = None,
    end_t_s: float | None = None,
) -> tuple[SimulateOut, SimResult]:
    """Propaga a missão de t = 0 (ou de `start`) até `end_t_s` (padrão: fim da missão)."""
    report = design_report(design)
    r_init, v_init = circular_orbit_state(
        initial_orbit.altitude_m, math.radians(initial_orbit.inclination_deg)
    )
    end = duration_s if end_t_s is None else end_t_s
    if start is None:
        r0, v0, stack, t0 = r_init, v_init, build_stack(report), 0.0
        pending = burns
    else:
        r0, v0, stack, t0 = start.r, start.v, start.stages, start.t_s
        # Manobras no próprio instante do checkpoint já foram aplicadas antes de salvá-lo.
        pending = [b for b in burns if b.t_s > start.t_s]
    pending = [b for b in pending if b.t_s <= end]
    if end <= t0:
        raise ValueError("O instante final deve ser posterior ao inicial.")

    settings = IntegratorSettings(rtol=rtol)
    started = time.perf_counter()
    res = propagate(
        r0,
        v0,
        stack,
        [Burn(b.t_s, b.dv_vnb_ms, b.label) for b in pending],
        end - t0,
        MU_EARTH,
        R_EARTH_EQ,
        n_samples=n_samples,
        settings=settings,
        t0=t0,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    final = None if res.terminated_early else summarize_earth(res.r[-1], res.v[-1])
    out = SimulateOut(
        design=DesignReportOut.from_domain(report),
        initial_orbit=orbit_out(summarize_earth(r_init, v_init)),
        final_orbit=orbit_out(final) if final else None,
        trajectory=Trajectory(
            t_s=res.t.tolist(),
            position_m=[tuple(p) for p in np.round(res.r, 3).tolist()],
            velocity_ms=[tuple(p) for p in np.round(res.v, 6).tolist()],
            mass_kg=res.mass.tolist(),
        ),
        events=[
            SimEventOut(t_s=e.t, kind=e.kind, message=e.message, data=e.data) for e in res.events
        ],
        delta_v_executed_ms=res.dv_executed_ms,
        propellant_used_kg=res.propellant_used_kg,
        final_mass_kg=float(res.mass[-1]),
        terminated_early=res.terminated_early,
        objective=_objective_out(objective, final),
        diagnostics=Diagnostics(
            integrator=INTEGRATOR_NAME,
            rtol=settings.rtol,
            atol_position_m=settings.atol_position_m,
            atol_velocity_ms=settings.atol_velocity_ms,
            function_evaluations=res.nfev,
            max_rel_energy_drift=res.max_rel_energy_drift,
            max_rel_angular_momentum_drift=res.max_rel_h_drift,
            compute_time_ms=elapsed_ms,
        ),
        provenance=provenance(
            "Propagação numérica de dois corpos com manobras impulsivas", SIM_ASSUMPTIONS
        ),
    )
    return out, res


def _objective_out(
    objective: ObjectiveIn | None, final: OrbitSummary | None
) -> ObjectiveOut | None:
    if objective is None:
        return None
    if final is None:
        return ObjectiveOut(
            achieved=False,
            periapsis_error_m=None,
            apoapsis_error_m=None,
            tolerance_m=objective.tolerance_m,
        )
    o = evaluate_circular_target(final, objective.target_altitude_m, objective.tolerance_m, False)
    return ObjectiveOut(
        achieved=o.achieved,
        periapsis_error_m=o.periapsis_error_m,
        apoapsis_error_m=o.apoapsis_error_m,
        tolerance_m=o.tolerance_m,
    )


def orbit_out(s: OrbitSummary) -> OrbitOut:
    return OrbitOut(
        orbit_type=s.orbit_type,
        semi_major_axis_m=s.elements.semi_major_axis,
        eccentricity=s.elements.eccentricity,
        inclination_deg=math.degrees(s.elements.inclination),
        periapsis_altitude_m=s.periapsis_radius - R_EARTH_EQ,
        apoapsis_altitude_m=None if s.apoapsis_radius is None else s.apoapsis_radius - R_EARTH_EQ,
        period_s=s.period,
        specific_energy_jkg=s.specific_energy,
        specific_angular_momentum_m2s=s.specific_angular_momentum,
    )


def provenance(model: str, assumptions: list[str]) -> Provenance:
    return Provenance(
        source="mission-architect/core",
        kind="calculated",
        computed_at=datetime.now(UTC),
        simulator_version=SIMULATOR_VERSION,
        model=model,
        reference_frame=FRAME,
        units=SI_UNITS,
        assumptions=assumptions,
    )

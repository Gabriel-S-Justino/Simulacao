from __future__ import annotations

import math
import time
from datetime import UTC, datetime

import numpy as np
from fastapi import APIRouter

from app.core.version import SIMULATOR_VERSION
from app.domain.constants import MU_EARTH, R_EARTH_EQ
from app.domain.orbital_mechanics.elements import OrbitSummary
from app.domain.spacecraft.catalog import Catalog, load_catalog
from app.domain.spacecraft.design import evaluate_design
from app.schemas.common import Provenance
from app.schemas.flight import (
    BurnOut,
    Diagnostics,
    Feasibility,
    HohmannIn,
    HohmannOut,
    ObjectiveOut,
    OrbitOut,
    SimEventOut,
    SimulateIn,
    SimulateOut,
    Trajectory,
)
from app.schemas.spacecraft import DesignIn, DesignReportOut
from app.services.flight import (
    build_stack,
    circular_orbit_state,
    evaluate_circular_target,
    plan_hohmann,
    summarize_earth,
)
from app.simulation.propagator import Burn, IntegratorSettings, propagate

router = APIRouter(prefix="/api/v1")

FRAME = "ECI inercial centrado na Terra (eixos tipo J2000; rotação da Terra não modelada)"
SI_UNITS = {"length": "m", "time": "s", "velocity": "m/s", "mass": "kg"}


@router.get("/health")
def health() -> dict[str, object]:
    catalog = load_catalog()
    return {
        "status": "ok",
        "version": SIMULATOR_VERSION,
        "catalog_version": catalog.version,
        "database": "not_configured",
        "time": datetime.now(UTC).isoformat(),
    }


@router.get("/catalog/components", response_model=Catalog)
def catalog_components() -> Catalog:
    return load_catalog()


@router.post("/spacecraft/evaluate", response_model=DesignReportOut)
def evaluate_spacecraft(design: DesignIn) -> DesignReportOut:
    report = evaluate_design(design.to_domain(), load_catalog().by_id())
    return DesignReportOut.from_domain(report)


@router.post("/planning/hohmann", response_model=HohmannOut)
def planning_hohmann(body: HohmannIn) -> HohmannOut:
    plan = plan_hohmann(body.initial_altitude_m, body.target_altitude_m, body.start_time_s)
    tr = plan.transfer
    feas = None
    if body.design is not None:
        report = evaluate_design(body.design.to_domain(), load_catalog().by_id())
        avail = report.total_delta_v_ms
        feas = Feasibility(
            available_delta_v_ms=avail,
            required_delta_v_ms=tr.total_dv,
            margin_ms=avail - tr.total_dv,
            feasible=avail >= tr.total_dv,
        )
    return HohmannOut(
        dv1_ms=tr.dv1,
        dv2_ms=tr.dv2,
        total_delta_v_ms=tr.total_dv,
        transfer_time_s=tr.transfer_time,
        transfer_semi_major_axis_m=tr.transfer_semi_major_axis,
        burns=[BurnOut(t_s=b.t, dv_vnb_ms=b.dv_vnb, label=b.label) for b in plan.burns],
        suggested_duration_s=plan.suggested_duration_s,
        feasibility=feas,
        provenance=_provenance(
            "Transferência de Hohmann analítica",
            ["Dois corpos", "Órbitas circulares coplanares", "Queimas impulsivas"],
        ),
    )


@router.post("/simulations/propagate", response_model=SimulateOut)
def simulate(body: SimulateIn) -> SimulateOut:
    report = evaluate_design(body.design.to_domain(), load_catalog().by_id())
    r0, v0 = circular_orbit_state(
        body.initial_orbit.altitude_m, math.radians(body.initial_orbit.inclination_deg)
    )
    settings = IntegratorSettings(rtol=body.integrator.rtol)
    started = time.perf_counter()
    res = propagate(
        r0,
        v0,
        build_stack(report),
        [Burn(b.t_s, b.dv_vnb_ms, b.label) for b in body.burns],
        body.duration_s,
        MU_EARTH,
        R_EARTH_EQ,
        n_samples=body.n_samples,
        settings=settings,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    initial = summarize_earth(r0, v0)
    final = None
    if not res.terminated_early:
        final = summarize_earth(res.r[-1], res.v[-1])
    objective = None
    if body.objective is not None:
        if final is None:
            objective = ObjectiveOut(
                achieved=False,
                periapsis_error_m=math.nan,
                apoapsis_error_m=None,
                tolerance_m=body.objective.tolerance_m,
            )
        else:
            o = evaluate_circular_target(
                final, body.objective.target_altitude_m, body.objective.tolerance_m, False
            )
            objective = ObjectiveOut(
                achieved=o.achieved,
                periapsis_error_m=o.periapsis_error_m,
                apoapsis_error_m=o.apoapsis_error_m,
                tolerance_m=o.tolerance_m,
            )

    return SimulateOut(
        design=DesignReportOut.from_domain(report),
        initial_orbit=_orbit_out(initial),
        final_orbit=_orbit_out(final) if final else None,
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
        objective=objective,
        diagnostics=Diagnostics(
            integrator="DOP853 (Runge-Kutta 8(5,3), passo adaptativo)",
            rtol=settings.rtol,
            atol_position_m=settings.atol_position_m,
            atol_velocity_ms=settings.atol_velocity_ms,
            function_evaluations=res.nfev,
            max_rel_energy_drift=res.max_rel_energy_drift,
            max_rel_angular_momentum_drift=res.max_rel_h_drift,
            compute_time_ms=elapsed_ms,
        ),
        provenance=_provenance(
            "Propagação numérica de dois corpos com manobras impulsivas",
            [
                "Terra como massa pontual (sem J2, arrasto ou terceiros corpos)",
                "Queimas impulsivas; duração finita estimada e sinalizada",
                "Órbita inicial circular com RAAN = 0 e argumento de latitude = 0",
            ],
        ),
    )


def _orbit_out(s: OrbitSummary) -> OrbitOut:
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


def _provenance(model: str, assumptions: list[str]) -> Provenance:
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

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.version import SIMULATOR_VERSION
from app.db.session import database_status
from app.domain.spacecraft.catalog import Catalog, load_catalog
from app.schemas.flight import (
    BurnOut,
    Feasibility,
    HohmannIn,
    HohmannOut,
    SimulateIn,
    SimulateOut,
)
from app.schemas.spacecraft import DesignIn, DesignReportOut
from app.services.flight import plan_hohmann
from app.services.simulation_runner import design_report, provenance, run_simulation

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health() -> dict[str, object]:
    catalog = load_catalog()
    return {
        "status": "ok",
        "version": SIMULATOR_VERSION,
        "catalog_version": catalog.version,
        "database": database_status(),
        "time": datetime.now(UTC).isoformat(),
    }


@router.get("/catalog/components", response_model=Catalog)
def catalog_components() -> Catalog:
    return load_catalog()


@router.post("/spacecraft/evaluate", response_model=DesignReportOut)
def evaluate_spacecraft(design: DesignIn) -> DesignReportOut:
    return DesignReportOut.from_domain(design_report(design))


@router.post("/planning/hohmann", response_model=HohmannOut)
def planning_hohmann(body: HohmannIn) -> HohmannOut:
    return hohmann_out(
        body.initial_altitude_m, body.target_altitude_m, body.start_time_s, body.design
    )


def hohmann_out(
    initial_altitude_m: float,
    target_altitude_m: float,
    start_time_s: float,
    design: DesignIn | None,
) -> HohmannOut:
    plan = plan_hohmann(initial_altitude_m, target_altitude_m, start_time_s)
    tr = plan.transfer
    feas = None
    if design is not None:
        avail = design_report(design).total_delta_v_ms
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
        provenance=provenance(
            "Transferência de Hohmann analítica",
            ["Dois corpos", "Órbitas circulares coplanares", "Queimas impulsivas"],
        ),
    )


@router.post("/simulations/propagate", response_model=SimulateOut)
def simulate(body: SimulateIn) -> SimulateOut:
    out, _ = run_simulation(
        body.design,
        body.initial_orbit,
        body.burns,
        body.duration_s,
        body.n_samples,
        body.objective,
        body.integrator.rtol,
    )
    return out

"""Ciclo de vida persistente da missão: plano, execução, checkpoints e retomada."""

from __future__ import annotations

import math
import uuid
from typing import Any

import numpy as np
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.version import SIMULATOR_VERSION
from app.models import Checkpoint, Mission, MissionRun
from app.repositories.missions import (
    MAX_CHECKPOINTS_PER_MISSION,
    get_checkpoint,
    trim_runs,
)
from app.schemas.flight import (
    BurnIn,
    CircularOrbitIn,
    Feasibility,
    IntegratorIn,
    ObjectiveIn,
    SimulateOut,
)
from app.schemas.missions import (
    CheckpointOut,
    MissionIn,
    MissionOut,
    MissionPatch,
    MissionRunOut,
    MissionValidationOut,
    StageStateOut,
    StateOut,
)
from app.schemas.spacecraft import DesignIn, DesignReportOut
from app.services.flight import build_stack, circular_orbit_state, plan_hohmann, summarize_earth
from app.services.simulation_runner import (
    INTEGRATOR_NAME,
    StartState,
    design_report,
    orbit_out,
    run_simulation,
)
from app.simulation.propagator import IntegratorSettings, StageTank

CHECKPOINT_SAMPLES = 16


def physics_config(integrator: IntegratorIn) -> dict[str, Any]:
    s = IntegratorSettings(rtol=integrator.rtol)
    return {
        "model": "two_body_point_mass",
        "maneuvers": "impulsive_vnb",
        "integrator": INTEGRATOR_NAME,
        "rtol": s.rtol,
        "atol_position_m": s.atol_position_m,
        "atol_velocity_ms": s.atol_velocity_ms,
    }


def create_mission(db: Session, body: MissionIn) -> Mission:
    design_report(body.design)  # valida IDs e limites antes de gravar
    mission = Mission(
        project_id=body.project_id,
        name=body.name,
        status="draft",
        design=body.design.model_dump(),
        initial_orbit=body.initial_orbit.model_dump(),
        objective=body.objective.model_dump() if body.objective else None,
        burns=[b.model_dump() for b in _sorted_burns(body.burns, body.duration_s)],
        duration_s=body.duration_s,
        physics=physics_config(body.integrator),
        seed=body.seed,
        simulator_version=SIMULATOR_VERSION,
    )
    db.add(mission)
    db.commit()
    return mission


def patch_mission(db: Session, mission: Mission, body: MissionPatch) -> Mission:
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes and body.name is not None:
        mission.name = body.name
    plan_fields = {
        "design",
        "initial_orbit",
        "objective",
        "burns",
        "duration_s",
        "seed",
        "integrator",
    }
    if plan_fields & changes.keys():
        if body.design is not None:
            design_report(body.design)
            mission.design = body.design.model_dump()
        if body.initial_orbit is not None:
            mission.initial_orbit = body.initial_orbit.model_dump()
        if "objective" in changes:
            mission.objective = body.objective.model_dump() if body.objective else None
        if body.duration_s is not None:
            mission.duration_s = body.duration_s
        if body.burns is not None:
            mission.burns = [b.model_dump() for b in body.burns]
        mission.burns = [b.model_dump() for b in _sorted_burns(_burns(mission), mission.duration_s)]
        if body.seed is not None:
            mission.seed = body.seed
        if body.integrator is not None:
            mission.physics = physics_config(body.integrator)
        _invalidate(mission)
    db.commit()
    return mission


def validate_mission(mission: Mission) -> MissionValidationOut:
    report = design_report(_design(mission))
    required = sum(math.sqrt(sum(c * c for c in b.dv_vnb_ms)) for b in _burns(mission))
    feas = Feasibility(
        available_delta_v_ms=report.total_delta_v_ms,
        required_delta_v_ms=required,
        margin_ms=report.total_delta_v_ms - required,
        feasible=report.total_delta_v_ms >= required,
    )
    return MissionValidationOut(
        design=DesignReportOut.from_domain(report),
        feasibility=feas,
        valid=report.valid and feas.feasible,
    )


def plan_mission(db: Session, mission: Mission, start_time_s: float) -> Mission:
    objective = _objective(mission)
    if objective is None:
        raise HTTPException(422, "A missão não tem objetivo de órbita definido.")
    plan = plan_hohmann(_orbit(mission).altitude_m, objective.target_altitude_m, start_time_s)
    mission.burns = [
        BurnIn(t_s=b.t, dv_vnb_ms=b.dv_vnb, label=b.label).model_dump() for b in plan.burns
    ]
    mission.duration_s = plan.suggested_duration_s
    _invalidate(mission)
    db.commit()
    return mission


def run_mission(
    db: Session, mission: Mission, n_samples: int, checkpoint_id: uuid.UUID | None = None
) -> MissionRunOut:
    start = None
    if checkpoint_id is not None:
        ck = get_checkpoint(db, mission, checkpoint_id)
        _require_version(ck.simulator_version)
        start = _start_state(ck)
    out = _simulate(mission, n_samples, start=start)
    run = MissionRun(
        mission_id=mission.id,
        from_checkpoint_id=checkpoint_id,
        summary=_summary(out),
        simulator_version=SIMULATOR_VERSION,
    )
    db.add(run)
    mission.status = "simulated"
    db.flush()
    db.refresh(mission)
    trim_runs(db, mission)
    db.commit()
    return MissionRunOut(run_id=run.id, from_checkpoint_id=checkpoint_id, simulation=out)


def create_checkpoint(db: Session, mission: Mission, t_s: float, label: str) -> Checkpoint:
    _require_version(mission.simulator_version)
    if not 0 <= t_s <= mission.duration_s:
        raise HTTPException(422, "Instante fora da duração da missão.")
    if len(mission.checkpoints) >= MAX_CHECKPOINTS_PER_MISSION:
        raise HTTPException(409, f"Limite de {MAX_CHECKPOINTS_PER_MISSION} checkpoints atingido.")
    state = initial_state(mission) if t_s == 0 else _state_at(mission, t_s)
    ck = Checkpoint(
        mission_id=mission.id,
        label=label or f"T+{t_s:.0f} s",
        t_s=t_s,
        state=state.model_dump(),
        simulator_version=SIMULATOR_VERSION,
    )
    db.add(ck)
    db.commit()
    return ck


def initial_state(mission: Mission) -> StateOut:
    orbit = _orbit(mission)
    r, v = circular_orbit_state(orbit.altitude_m, math.radians(orbit.inclination_deg))
    stack = build_stack(design_report(_design(mission)))
    return _state_out("initial", 0.0, r, v, stack)


def latest_state(mission: Mission) -> StateOut:
    if not mission.checkpoints:
        return initial_state(mission)
    ck = max(mission.checkpoints, key=lambda c: c.t_s)
    return StateOut.model_validate(ck.state)


def checkpoint_out(ck: Checkpoint) -> CheckpointOut:
    return CheckpointOut(
        id=ck.id,
        mission_id=ck.mission_id,
        label=ck.label,
        t_s=ck.t_s,
        state=StateOut.model_validate(ck.state),
        simulator_version=ck.simulator_version,
        created_at=ck.created_at,
    )


def mission_out(m: Mission) -> MissionOut:
    return MissionOut(
        id=m.id,
        project_id=m.project_id,
        name=m.name,
        status="simulated" if m.status == "simulated" else "draft",
        design=_design(m),
        initial_orbit=_orbit(m),
        objective=_objective(m),
        burns=_burns(m),
        duration_s=m.duration_s,
        physics=m.physics,
        seed=m.seed,
        simulator_version=m.simulator_version,
        created_at=m.created_at,
        updated_at=m.updated_at,
        checkpoint_count=len(m.checkpoints),
        run_count=len(m.runs),
    )


# --- auxiliares ---------------------------------------------------------------


def _simulate(
    mission: Mission, n_samples: int, start: StartState | None = None, end_t_s: float | None = None
) -> SimulateOut:
    out, _ = run_simulation(
        _design(mission),
        _orbit(mission),
        _burns(mission),
        mission.duration_s,
        n_samples,
        _objective(mission),
        float(mission.physics["rtol"]),
        start=start,
        end_t_s=end_t_s,
    )
    return out


def _state_at(mission: Mission, t_s: float) -> StateOut:
    _, res = run_simulation(
        _design(mission),
        _orbit(mission),
        _burns(mission),
        mission.duration_s,
        CHECKPOINT_SAMPLES,
        None,
        float(mission.physics["rtol"]),
        end_t_s=t_s,
    )
    if res.terminated_early:
        raise HTTPException(422, "A nave impactou antes deste instante.")
    return _state_out("checkpoint", t_s, res.r[-1], res.v[-1], list(res.final_stages))


def _state_out(
    source: str, t_s: float, r: np.ndarray, v: np.ndarray, stages: list[StageTank]
) -> StateOut:
    return StateOut(
        source="checkpoint" if source == "checkpoint" else "initial",
        t_s=t_s,
        position_m=(float(r[0]), float(r[1]), float(r[2])),
        velocity_ms=(float(v[0]), float(v[1]), float(v[2])),
        mass_kg=sum(s.burnable_kg + s.jettison_mass_kg for s in stages),
        stages=[
            StageStateOut(
                name=s.name,
                burnable_kg=s.burnable_kg,
                isp_s=s.isp_s,
                thrust_n=s.thrust_n,
                jettison_mass_kg=s.jettison_mass_kg,
            )
            for s in stages
        ],
        orbit=orbit_out(summarize_earth(r, v)),
    )


def _start_state(ck: Checkpoint) -> StartState:
    st = StateOut.model_validate(ck.state)
    return StartState(
        t_s=st.t_s,
        r=np.array(st.position_m, dtype=np.float64),
        v=np.array(st.velocity_ms, dtype=np.float64),
        stages=[
            StageTank(s.name, s.burnable_kg, s.isp_s, s.thrust_n, s.jettison_mass_kg)
            for s in st.stages
        ],
    )


def _summary(out: SimulateOut) -> dict[str, Any]:
    data = out.model_dump(mode="json", exclude={"trajectory"})
    data["trajectory_samples"] = len(out.trajectory.t_s)
    return data


def _invalidate(mission: Mission) -> None:
    """Plano alterado: checkpoints e relatórios anteriores deixam de valer."""
    mission.checkpoints.clear()
    mission.runs.clear()
    mission.status = "draft"
    mission.simulator_version = SIMULATOR_VERSION


def _require_version(version: str) -> None:
    if version != SIMULATOR_VERSION:
        raise HTTPException(
            409,
            f"Gravado com o simulador {version}; versão atual {SIMULATOR_VERSION}. "
            "Replaneje a missão para reproduzir com a versão atual.",
        )


def _sorted_burns(burns: list[BurnIn], duration_s: float) -> list[BurnIn]:
    for b in burns:
        if b.t_s > duration_s:
            raise HTTPException(422, "Manobra após o fim da missão.")
    return sorted(burns, key=lambda b: b.t_s)


def _design(m: Mission) -> DesignIn:
    return DesignIn.model_validate(m.design)


def _orbit(m: Mission) -> CircularOrbitIn:
    return CircularOrbitIn.model_validate(m.initial_orbit)


def _objective(m: Mission) -> ObjectiveIn | None:
    return None if m.objective is None else ObjectiveIn.model_validate(m.objective)


def _burns(m: Mission) -> list[BurnIn]:
    return [BurnIn.model_validate(b) for b in m.burns]

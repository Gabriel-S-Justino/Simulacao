from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project
from app.repositories.missions import (
    get_mission,
    get_project,
    list_missions,
    list_projects,
)
from app.schemas.missions import (
    CheckpointIn,
    CheckpointOut,
    MissionIn,
    MissionOut,
    MissionPatch,
    MissionRunOut,
    MissionValidationOut,
    PlanIn,
    ProjectIn,
    ProjectOut,
    RunIn,
    RunSummaryOut,
    StateOut,
)
from app.services import missions as svc

router = APIRouter(prefix="/api/v1")
Db = Depends(get_db)


@router.get("/projects", response_model=list[ProjectOut])
def projects(db: Session = Db) -> list[ProjectOut]:
    return [
        ProjectOut(id=p.id, name=p.name, created_at=p.created_at, mission_count=n)
        for p, n in list_projects(db)
    ]


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: Session = Db) -> ProjectOut:
    p = Project(name=body.name)
    db.add(p)
    db.commit()
    return ProjectOut(id=p.id, name=p.name, created_at=p.created_at, mission_count=0)


@router.get("/missions", response_model=list[MissionOut])
def missions(project_id: uuid.UUID | None = None, db: Session = Db) -> list[MissionOut]:
    return [svc.mission_out(m) for m in list_missions(db, project_id)]


@router.post("/missions", response_model=MissionOut, status_code=201)
def create_mission(body: MissionIn, db: Session = Db) -> MissionOut:
    get_project(db, body.project_id)
    return svc.mission_out(svc.create_mission(db, body))


@router.get("/missions/{mission_id}", response_model=MissionOut)
def mission(mission_id: uuid.UUID, db: Session = Db) -> MissionOut:
    return svc.mission_out(get_mission(db, mission_id))


@router.patch("/missions/{mission_id}", response_model=MissionOut)
def patch_mission(mission_id: uuid.UUID, body: MissionPatch, db: Session = Db) -> MissionOut:
    return svc.mission_out(svc.patch_mission(db, get_mission(db, mission_id), body))


@router.delete("/missions/{mission_id}", status_code=204)
def delete_mission(mission_id: uuid.UUID, db: Session = Db) -> None:
    db.delete(get_mission(db, mission_id))
    db.commit()


@router.post("/missions/{mission_id}/validate", response_model=MissionValidationOut)
def validate(mission_id: uuid.UUID, db: Session = Db) -> MissionValidationOut:
    return svc.validate_mission(get_mission(db, mission_id))


@router.post("/missions/{mission_id}/plan", response_model=MissionOut)
def plan(mission_id: uuid.UUID, body: PlanIn, db: Session = Db) -> MissionOut:
    return svc.mission_out(svc.plan_mission(db, get_mission(db, mission_id), body.start_time_s))


@router.post("/missions/{mission_id}/run", response_model=MissionRunOut)
def run(mission_id: uuid.UUID, body: RunIn, db: Session = Db) -> MissionRunOut:
    return svc.run_mission(db, get_mission(db, mission_id), body.n_samples)


@router.get("/missions/{mission_id}/state", response_model=StateOut)
def state(mission_id: uuid.UUID, db: Session = Db) -> StateOut:
    return svc.latest_state(get_mission(db, mission_id))


@router.get("/missions/{mission_id}/checkpoints", response_model=list[CheckpointOut])
def checkpoints(mission_id: uuid.UUID, db: Session = Db) -> list[CheckpointOut]:
    return [svc.checkpoint_out(c) for c in get_mission(db, mission_id).checkpoints]


@router.post("/missions/{mission_id}/checkpoints", response_model=CheckpointOut, status_code=201)
def create_checkpoint(mission_id: uuid.UUID, body: CheckpointIn, db: Session = Db) -> CheckpointOut:
    ck = svc.create_checkpoint(db, get_mission(db, mission_id), body.t_s, body.label)
    return svc.checkpoint_out(ck)


@router.post(
    "/missions/{mission_id}/checkpoints/{checkpoint_id}/resume", response_model=MissionRunOut
)
def resume(
    mission_id: uuid.UUID, checkpoint_id: uuid.UUID, body: RunIn, db: Session = Db
) -> MissionRunOut:
    return svc.run_mission(db, get_mission(db, mission_id), body.n_samples, checkpoint_id)


@router.get("/missions/{mission_id}/reports", response_model=list[RunSummaryOut])
def reports(mission_id: uuid.UUID, db: Session = Db) -> list[RunSummaryOut]:
    return [
        RunSummaryOut(
            id=r.id,
            from_checkpoint_id=r.from_checkpoint_id,
            simulator_version=r.simulator_version,
            created_at=r.created_at,
            summary=r.summary,
        )
        for r in reversed(get_mission(db, mission_id).runs)
    ]

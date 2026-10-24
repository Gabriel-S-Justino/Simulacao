from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Checkpoint, Mission, Project

MAX_PROJECTS_LISTED = 200
MAX_MISSIONS_LISTED = 200
MAX_CHECKPOINTS_PER_MISSION = 50
MAX_RUNS_KEPT = 20


def get_project(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Projeto não encontrado.")
    return project


def list_projects(db: Session) -> list[tuple[Project, int]]:
    count = (
        select(Mission.project_id, func.count(Mission.id).label("n"))
        .group_by(Mission.project_id)
        .subquery()
    )
    rows = db.execute(
        select(Project, func.coalesce(count.c.n, 0))
        .outerjoin(count, count.c.project_id == Project.id)
        .order_by(Project.created_at.desc())
        .limit(MAX_PROJECTS_LISTED)
    ).all()
    return [(p, int(n)) for p, n in rows]


def get_mission(db: Session, mission_id: uuid.UUID) -> Mission:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(404, "Missão não encontrada.")
    return mission


def list_missions(db: Session, project_id: uuid.UUID | None) -> list[Mission]:
    stmt = select(Mission).order_by(Mission.updated_at.desc()).limit(MAX_MISSIONS_LISTED)
    if project_id is not None:
        stmt = stmt.where(Mission.project_id == project_id)
    return list(db.scalars(stmt))


def get_checkpoint(db: Session, mission: Mission, checkpoint_id: uuid.UUID) -> Checkpoint:
    ck = db.get(Checkpoint, checkpoint_id)
    if ck is None or ck.mission_id != mission.id:
        raise HTTPException(404, "Checkpoint não encontrado.")
    return ck


def trim_runs(db: Session, mission: Mission) -> None:
    """Mantém apenas os relatórios mais recentes de cada missão."""
    excess = len(mission.runs) - MAX_RUNS_KEPT
    for run in list(mission.runs)[: max(0, excess)]:
        db.delete(run)

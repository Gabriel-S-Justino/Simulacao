"""Modelos ORM. A trajetória completa não é gravada: é reproduzível a partir do plano,
da versão do simulador, da configuração física e da semente."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JsonType = JSON().with_variant(JSONB(), "postgresql")


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {dict[str, Any]: JsonType, list[Any]: JsonType}


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    missions: Mapped[list[Mission]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | simulated
    design: Mapped[dict[str, Any]]
    initial_orbit: Mapped[dict[str, Any]]
    objective: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    burns: Mapped[list[Any]]
    duration_s: Mapped[float] = mapped_column(Float)
    physics: Mapped[dict[str, Any]]  # modelo, integrador, tolerâncias
    seed: Mapped[int] = mapped_column(Integer)
    simulator_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    project: Mapped[Project] = relationship(back_populates="missions")
    checkpoints: Mapped[list[Checkpoint]] = relationship(
        back_populates="mission", cascade="all, delete-orphan", order_by="Checkpoint.t_s"
    )
    runs: Mapped[list[MissionRun]] = relationship(
        back_populates="mission", cascade="all, delete-orphan", order_by="MissionRun.created_at"
    )


class Checkpoint(Base):
    """Snapshot consistente do estado físico num instante (posição, velocidade, estágios)."""

    __tablename__ = "checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(64))
    t_s: Mapped[float] = mapped_column(Float)
    state: Mapped[dict[str, Any]]
    simulator_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    mission: Mapped[Mission] = relationship(back_populates="checkpoints")


class MissionRun(Base):
    """Resultado (relatório) de uma execução: resumo, eventos e diagnósticos, sem amostras."""

    __tablename__ = "mission_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), index=True
    )
    from_checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    summary: Mapped[dict[str, Any]]
    simulator_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    mission: Mapped[Mission] = relationship(back_populates="runs")

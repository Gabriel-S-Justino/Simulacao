"""Engine e sessões SQLAlchemy. O banco é opcional: sem DATABASE_URL, as rotas de missões
respondem 503 e o restante da API continua funcionando."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def normalize_url(url: str) -> str:
    """Aceita URLs no formato do Neon/Heroku (`postgres://`, `postgresql://`) e usa o psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine | None:
    settings = get_settings()
    if not settings.database_url:
        return None
    url = normalize_url(settings.database_url)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    if settings.database_pooling:
        return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    # Funções serverless (Vercel): sem pool local; o pooler do Neon gerencia conexões.
    return create_engine(url, poolclass=NullPool)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session] | None:
    engine = get_engine()
    return None if engine is None else sessionmaker(engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    factory = _session_factory()
    if factory is None:
        raise HTTPException(503, "Persistência não configurada (DATABASE_URL ausente).")
    with factory() as session:
        yield session


def database_status() -> str:
    engine = get_engine()
    if engine is None:
        return "not_configured"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"


def reset_engine_cache() -> None:
    get_engine.cache_clear()
    _session_factory.cache_clear()

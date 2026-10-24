"""Rotas das fontes externas. Todas devolvem o envelope §4.9.

O HTTP 200 significa que esta API respondeu; o estado da fonte externa está em
``status`` (ok, stale, error, not_configured). Parâmetros inválidos dão 422.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.integrations import apod, donki, eonet, epic, gibs, jpl, neows, open_notify
from app.integrations.donki import CoronalMassEjection, GeomagneticStorm, SolarFlare
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient
from app.integrations.keys import nasa_key

router = APIRouter(prefix="/api/v1")


@lru_cache
def _shared_client() -> ExternalClient:
    s = get_settings()
    return ExternalClient(
        timeout_s=s.external_timeout_seconds, max_stale_s=s.external_max_stale_seconds
    )


def get_external_client() -> ExternalClient:
    return _shared_client()


Client = Annotated[ExternalClient, Depends(get_external_client)]
Config = Annotated[Settings, Depends(get_settings)]


def _naive_utc(t: datetime) -> datetime:
    return t.astimezone(UTC).replace(tzinfo=None) if t.tzinfo else t


def _today() -> date:
    return datetime.now(UTC).date()


class SourceInfo(BaseModel):
    id: str
    name: str
    endpoint: str
    needs_nasa_key: bool
    configured: bool
    notes: list[str]


@router.get("/sources", response_model=list[SourceInfo])
def sources(settings: Config) -> list[SourceInfo]:
    """Estado de configuração de cada fonte (não faz requisições externas)."""
    key = nasa_key(settings)
    key_notes = list(key.notes) + ([key.error.message] if key.error else [])
    rows = [
        ("gibs", "NASA GIBS", "/api/v1/earth/imagery/layers", False),
        ("epic", "NASA EPIC", "/api/v1/earth/epic", False),
        ("eonet", "NASA EONET", "/api/v1/events/earth", False),
        ("donki", "NASA DONKI", "/api/v1/events/space-weather", True),
        ("horizons", "JPL Horizons", "/api/v1/ephemerides", False),
        ("sbdb", "JPL SBDB", "/api/v1/small-bodies", False),
        ("cad", "JPL CNEOS CAD", "/api/v1/asteroids/close-approaches", False),
        ("neows", "NASA NeoWs", "/api/v1/asteroids/feed", True),
        ("apod", "NASA APOD", "/api/v1/apod", True),
        ("iss", "Open Notify ISS", "/api/v1/iss/position", False),
    ]
    return [
        SourceInfo(
            id=i,
            name=n,
            endpoint=e,
            needs_nasa_key=k,
            configured=key.value is not None if k else True,
            notes=key_notes if k else [],
        )
        for i, n, e, k in rows
    ]


@router.get("/earth/imagery/layers", response_model=SourceEnvelope[gibs.GibsCatalog])
def gibs_layers(client: Client, settings: Config) -> SourceEnvelope[gibs.GibsCatalog]:
    return gibs.fetch_layers(client, settings)


@router.get("/earth/epic", response_model=SourceEnvelope[list[epic.EpicImage]])
def epic_images(
    client: Client, settings: Config, day: Annotated[date | None, Query(alias="date")] = None
) -> SourceEnvelope[list[epic.EpicImage]]:
    if day is not None and day > _today():
        raise ValueError("Data futura.")
    return epic.fetch_epic(client, settings, day)


@router.get("/events/earth", response_model=SourceEnvelope[list[eonet.EarthEvent]])
def earth_events(
    client: Client,
    settings: Config,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    status: Literal["open", "closed", "all"] = "open",
    category: Annotated[str | None, Query(pattern=r"^[A-Za-z]{1,40}$")] = None,
) -> SourceEnvelope[list[eonet.EarthEvent]]:
    return eonet.fetch_events(
        client, settings, days=days, limit=limit, status=status, category=category
    )


class SpaceWeatherOut(BaseModel):
    start: date
    end: date
    flares: SourceEnvelope[list[SolarFlare]]
    storms: SourceEnvelope[list[GeomagneticStorm]]
    cmes: SourceEnvelope[list[CoronalMassEjection]]


@router.get("/events/space-weather", response_model=SpaceWeatherOut)
def space_weather(
    client: Client,
    settings: Config,
    days: Annotated[int, Query(ge=1, le=donki.MAX_DAYS)] = 7,
) -> SpaceWeatherOut:
    end = _today()
    start = end - timedelta(days=days)
    out = donki.fetch_space_weather(client, settings, start, end)
    return SpaceWeatherOut.model_validate(
        {"start": start, "end": end, **{k: v.model_dump() for k, v in out.items()}}
    )


@router.get("/ephemerides", response_model=SourceEnvelope[jpl.HorizonsVectors])
def ephemerides(
    client: Client,
    settings: Config,
    target: str = "301",
    center: str = "500@399",
    start: datetime | None = None,
    stop: datetime | None = None,
    step: str = "1 h",
) -> SourceEnvelope[jpl.HorizonsVectors]:
    """Vetores de estado do Horizons (instantes interpretados em TDB pela fonte)."""
    t0 = _naive_utc(start or datetime.now(UTC).replace(minute=0, second=0, microsecond=0))
    t1 = _naive_utc(stop) if stop else t0 + timedelta(days=1)
    return jpl.fetch_horizons_vectors(
        client, settings, target=target, center=center, start=t0, stop=t1, step=step
    )


@router.get("/small-bodies", response_model=SourceEnvelope[jpl.SmallBody])
def small_body(
    client: Client, settings: Config, q: Annotated[str, Query(min_length=1, max_length=40)]
) -> SourceEnvelope[jpl.SmallBody]:
    return jpl.fetch_small_body(client, settings, q)


@router.get("/asteroids/close-approaches", response_model=SourceEnvelope[list[jpl.CloseApproach]])
def close_approaches(
    client: Client,
    settings: Config,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    dist_max_au: Annotated[float, Query(gt=0, le=0.5)] = 0.05,
) -> SourceEnvelope[list[jpl.CloseApproach]]:
    return jpl.fetch_close_approaches(client, settings, days=days, dist_max_au=dist_max_au)


@router.get("/asteroids/feed", response_model=SourceEnvelope[neows.NeoFeed])
def asteroid_feed(
    client: Client,
    settings: Config,
    start: date | None = None,
    end: date | None = None,
) -> SourceEnvelope[neows.NeoFeed]:
    s = start or _today()
    e = end or s + timedelta(days=neows.MAX_FEED_DAYS - 1)
    return neows.fetch_feed(client, settings, s, e)


@router.get("/apod", response_model=SourceEnvelope[apod.Apod])
def astronomy_picture(
    client: Client, settings: Config, day: Annotated[date | None, Query(alias="date")] = None
) -> SourceEnvelope[apod.Apod]:
    if day is not None and not (apod.FIRST_APOD <= day <= _today()):
        raise ValueError(f"Data do APOD deve estar entre {apod.FIRST_APOD} e hoje.")
    return apod.fetch_apod(client, settings, day)


@router.get("/iss/position", response_model=SourceEnvelope[open_notify.IssPosition])
def iss_position(client: Client, settings: Config) -> SourceEnvelope[open_notify.IssPosition]:
    return open_notify.fetch_iss(client, settings)

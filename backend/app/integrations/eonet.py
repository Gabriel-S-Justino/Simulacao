"""NASA EONET v3 (Earth Observatory Natural Event Tracker), /api/v3/events.

Docs: https://eonet.gsfc.nasa.gov/docs/v3. A própria NASA alerta que o EONET não é
fonte oficial para dados espaciais ou temporais precisos; isso vai em ``notes``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

import httpx
from pydantic import BaseModel, Field, field_validator

from app.core.config import Settings
from app.integrations.common import HttpUrlStr, Raw
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient, Parsed, SourceMeta
from app.integrations.timeutil import parse_utc

META = SourceMeta(
    source="NASA EONET v3",
    units={"lon_deg": "deg", "lat_deg": "deg", "date": "UTC"},
    reference_frame="Geográfica (longitude, latitude; GeoJSON, WGS 84)",
    uncertainty="Posições e datas aproximadas; datas costumam ser 00:00Z do dia.",
    attribution="NASA Earth Observatory Natural Event Tracker (EONET)",
    notes=("EONET não deve ser tratado como fonte oficial de posição ou horário precisos.",),
)


class _Category(Raw):
    id: str
    title: str

    @field_validator("id", mode="before")
    @classmethod
    def _str_id(cls, v: object) -> object:
        return str(v) if isinstance(v, int) else v


class _Source(Raw):
    id: str
    url: HttpUrlStr | None = None


class _Geometry(Raw):
    date: str
    type: Literal["Point", "Polygon"]
    coordinates: list[float] | list[list[list[float]]]
    magnitudeValue: float | None = None  # noqa: N815
    magnitudeUnit: str | None = None  # noqa: N815


class _Event(Raw):
    id: str
    title: str
    description: str | None = None
    link: HttpUrlStr | None = None
    closed: str | None = None
    categories: list[_Category]
    sources: list[_Source] = Field(default_factory=list)
    geometry: list[_Geometry]


class _Response(Raw):
    events: list[_Event]


class EventCategory(BaseModel):
    id: str
    title: str


class EventGeometry(BaseModel):
    date: datetime
    kind: Literal["point", "polygon"]
    lon_deg: float
    lat_deg: float
    point_method: Literal["point", "polygon_vertex_mean"]
    polygon: list[tuple[float, float]] | None
    magnitude_value: float | None
    magnitude_unit: str | None


class EarthEvent(BaseModel):
    id: str
    title: str
    description: str | None
    link: str | None
    closed: datetime | None
    categories: list[EventCategory]
    source_ids: list[str]
    geometry: list[EventGeometry]


def _lonlat(pair: list[float]) -> tuple[float, float]:
    lon, lat = float(pair[0]), float(pair[1])
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise ValueError("EONET: coordenada fora do intervalo geográfico")
    return lon, lat


def _geometry(g: _Geometry) -> EventGeometry:
    if g.type == "Point":
        coords = g.coordinates
        if not coords or isinstance(coords[0], list):
            raise ValueError("EONET: Point com coordenadas inválidas")
        lon, lat = _lonlat(coords)
        return EventGeometry(
            date=parse_utc(g.date),
            kind="point",
            lon_deg=lon,
            lat_deg=lat,
            point_method="point",
            polygon=None,
            magnitude_value=g.magnitudeValue,
            magnitude_unit=g.magnitudeUnit,
        )
    rings = g.coordinates
    if not rings or not isinstance(rings[0], list) or not rings[0]:
        raise ValueError("EONET: Polygon com coordenadas inválidas")
    ring = [_lonlat(p) for p in rings[0]]
    # Ponto de exibição: média dos vértices do anel externo (rotulado; não vem da fonte).
    verts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    lon = sum(p[0] for p in verts) / len(verts)
    lat = sum(p[1] for p in verts) / len(verts)
    return EventGeometry(
        date=parse_utc(g.date),
        kind="polygon",
        lon_deg=lon,
        lat_deg=lat,
        point_method="polygon_vertex_mean",
        polygon=ring,
        magnitude_value=g.magnitudeValue,
        magnitude_unit=g.magnitudeUnit,
    )


def parse_events(resp: httpx.Response) -> Parsed[list[EarthEvent]]:
    body = _Response.model_validate(resp.json())
    out: list[EarthEvent] = []
    for e in body.events:
        geoms = sorted((_geometry(g) for g in e.geometry), key=lambda g: g.date)
        out.append(
            EarthEvent(
                id=e.id,
                title=e.title,
                description=e.description,
                link=e.link,
                closed=parse_utc(e.closed) if e.closed else None,
                categories=[EventCategory(id=c.id, title=c.title) for c in e.categories],
                source_ids=[s.id for s in e.sources],
                geometry=geoms,
            )
        )
    dates = [g.date for e in out for g in e.geometry]
    return Parsed(
        out,
        observed_at=max(dates) if dates else None,
        valid_time_start=min(dates) if dates else None,
        valid_time_end=max(dates) if dates else None,
    )


def fetch_events(
    client: ExternalClient,
    settings: Settings,
    *,
    days: int,
    limit: int,
    status: Literal["open", "closed", "all"] = "open",
    category: str | None = None,
) -> SourceEnvelope[list[EarthEvent]]:
    params: dict[str, str | int | float] = {"status": status, "days": days, "limit": limit}
    if category:
        params["category"] = category
    return client.fetch(
        META,
        f"{settings.eonet_base_url}/api/v3/events",
        params=params,
        cache_key=f"eonet:{status}:{days}:{limit}:{category or ''}",
        ttl_s=min(settings.nasa_cache_ttl_seconds, 1800),
        parse=parse_events,
    )

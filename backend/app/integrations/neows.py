"""NASA NeoWs (Near Earth Object Web Service), endpoint /feed.

Docs: https://api.nasa.gov (seção Asteroids - NeoWs). O feed aceita no máximo 7 dias.
NeoWs envia vários números como strings; a validação converte e rejeita o que não for número.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime

import httpx
from pydantic import BaseModel

from app.core.config import Settings
from app.integrations.common import KM_M, HttpUrlStr, Raw
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient, Parsed, SourceMeta
from app.integrations.keys import nasa_key
from app.integrations.timeutil import day_end, day_start

MAX_FEED_DAYS = 7

META = SourceMeta(
    source="NASA NeoWs",
    units={
        "diameter_min_m": "m",
        "diameter_max_m": "m",
        "miss_distance_m": "m",
        "relative_velocity_ms": "m/s",
        "absolute_magnitude_h": "mag",
    },
    reference_frame="Distância e velocidade relativas ao corpo de aproximação (orbiting_body)",
    uncertainty=(
        "Diâmetro estimado a partir de H com faixa de albedo (min-max); "
        "não é medida direta. Para incertezas orbitais, usar SBDB/CAD."
    ),
    attribution="NASA/JPL Asteroids - NeoWs (api.nasa.gov)",
)


class _Diameter(Raw):
    estimated_diameter_min: float
    estimated_diameter_max: float


class _Diameters(Raw):
    meters: _Diameter


class _Velocity(Raw):
    kilometers_per_second: float


class _Miss(Raw):
    kilometers: float


class _Approach(Raw):
    epoch_date_close_approach: int
    close_approach_date_full: str | None = None
    relative_velocity: _Velocity
    miss_distance: _Miss
    orbiting_body: str


class _Neo(Raw):
    id: str
    name: str
    nasa_jpl_url: HttpUrlStr | None = None
    absolute_magnitude_h: float
    estimated_diameter: _Diameters
    is_potentially_hazardous_asteroid: bool
    is_sentry_object: bool = False
    close_approach_data: list[_Approach]


class _Feed(Raw):
    element_count: int
    near_earth_objects: dict[str, list[_Neo]]


class NeoApproach(BaseModel):
    id: str
    name: str
    absolute_magnitude_h: float
    diameter_min_m: float
    diameter_max_m: float
    potentially_hazardous: bool
    sentry_object: bool
    close_approach_epoch: datetime
    close_approach_label: str | None
    relative_velocity_ms: float
    miss_distance_m: float
    orbiting_body: str
    jpl_url: str | None


class NeoFeed(BaseModel):
    element_count: int
    approaches: list[NeoApproach]


def make_parser(start: date, end: date) -> Callable[[httpx.Response], Parsed[NeoFeed]]:
    def parse(resp: httpx.Response) -> Parsed[NeoFeed]:
        feed = _Feed.model_validate(resp.json())
        out: list[NeoApproach] = []
        for neos in feed.near_earth_objects.values():
            for neo in neos:
                d = neo.estimated_diameter.meters
                for ca in neo.close_approach_data:
                    out.append(
                        NeoApproach(
                            id=neo.id,
                            name=neo.name,
                            absolute_magnitude_h=neo.absolute_magnitude_h,
                            diameter_min_m=d.estimated_diameter_min,
                            diameter_max_m=d.estimated_diameter_max,
                            potentially_hazardous=neo.is_potentially_hazardous_asteroid,
                            sentry_object=neo.is_sentry_object,
                            close_approach_epoch=datetime.fromtimestamp(
                                ca.epoch_date_close_approach / 1000, tz=UTC
                            ),
                            close_approach_label=ca.close_approach_date_full,
                            relative_velocity_ms=ca.relative_velocity.kilometers_per_second * KM_M,
                            miss_distance_m=ca.miss_distance.kilometers * KM_M,
                            orbiting_body=ca.orbiting_body,
                            jpl_url=neo.nasa_jpl_url,
                        )
                    )
        out.sort(key=lambda a: a.close_approach_epoch)
        return Parsed(
            NeoFeed(element_count=feed.element_count, approaches=out),
            valid_time_start=day_start(start),
            valid_time_end=day_end(end),
            notes=(
                "Instante de aproximação a partir de epoch_date_close_approach; a escala de "
                "tempo exata não é documentada pela NeoWs (o CAD do JPL usa TDB).",
            ),
        )

    return parse


def fetch_feed(
    client: ExternalClient, settings: Settings, start: date, end: date
) -> SourceEnvelope[NeoFeed]:
    if end < start or (end - start).days >= MAX_FEED_DAYS:
        raise ValueError(f"Intervalo do feed NeoWs deve ter de 1 a {MAX_FEED_DAYS} dias.")
    key = nasa_key(settings)
    meta = replace(META, notes=META.notes + key.notes)
    if key.value is None:
        assert key.error is not None
        return ExternalClient.failed(meta, key.error)
    return client.fetch(
        meta,
        f"{settings.nasa_api_base_url}/neo/rest/v1/feed",
        params={"start_date": start.isoformat(), "end_date": end.isoformat(), "api_key": key.value},
        cache_key=f"neows:{start}:{end}",
        ttl_s=settings.nasa_cache_ttl_seconds,
        parse=make_parser(start, end),
    )

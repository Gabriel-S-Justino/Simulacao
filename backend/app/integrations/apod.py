"""NASA APOD (Astronomy Picture of the Day). Docs: https://github.com/nasa/apod-api"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import httpx
from pydantic import BaseModel

from app.core.config import Settings
from app.integrations.common import HttpUrlStr, Raw
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient, Parsed, SourceMeta
from app.integrations.keys import nasa_key
from app.integrations.timeutil import day_end, day_start

FIRST_APOD = date(1995, 6, 16)

META = SourceMeta(
    source="NASA APOD",
    attribution="NASA Astronomy Picture of the Day (apod.nasa.gov). Créditos por imagem.",
    notes=("Conteúdo editorial/educacional; não é dado científico de missão.",),
)


class ApodRaw(Raw):
    date: date
    title: str
    explanation: str
    media_type: str
    url: HttpUrlStr | None = None
    hdurl: HttpUrlStr | None = None
    thumbnail_url: HttpUrlStr | None = None
    copyright: str | None = None


class Apod(BaseModel):
    date: date
    title: str
    explanation: str
    media_type: str
    url: str | None
    hdurl: str | None
    thumbnail_url: str | None
    copyright: str | None
    page_url: str


def parse_apod(resp: httpx.Response) -> Parsed[Apod]:
    raw = ApodRaw.model_validate(resp.json())
    page = f"https://apod.nasa.gov/apod/ap{raw.date:%y%m%d}.html"
    data = Apod(**raw.model_dump(), page_url=page)
    return Parsed(data, valid_time_start=day_start(raw.date), valid_time_end=day_end(raw.date))


def fetch_apod(
    client: ExternalClient, settings: Settings, day: date | None
) -> SourceEnvelope[Apod]:
    key = nasa_key(settings)
    meta = replace(META, notes=META.notes + key.notes)
    if key.value is None:
        assert key.error is not None
        return ExternalClient.failed(meta, key.error)
    params: dict[str, str | int | float] = {"api_key": key.value, "thumbs": "true"}
    if day is not None:
        params["date"] = day.isoformat()
    return client.fetch(
        meta,
        f"{settings.nasa_api_base_url}/planetary/apod",
        params=params,
        cache_key=f"apod:{day or 'today'}",
        ttl_s=settings.nasa_cache_ttl_seconds,
        parse=parse_apod,
    )

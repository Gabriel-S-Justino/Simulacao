"""NASA EPIC (DSCOVR Earth Polychromatic Imaging Camera), coleção "natural".

Docs: https://epic.gsfc.nasa.gov/about/api. Consumido direto de epic.gsfc.nasa.gov
(não exige chave). Imagens: /archive/natural/{YYYY}/{MM}/{DD}/{png|jpg|thumbs}/{image}.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

import httpx
from pydantic import BaseModel

from app.core.config import Settings
from app.integrations.common import Raw
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient, Parsed, SourceMeta
from app.integrations.timeutil import parse_utc

META = SourceMeta(
    source="NASA EPIC (DSCOVR)",
    units={
        "dscovr_position_km": "km",
        "lunar_position_km": "km",
        "sun_position_km": "km",
        "centroid_lat_deg": "deg",
        "centroid_lon_deg": "deg",
        "observed_at": "UTC",
    },
    reference_frame="J2000 geocêntrico (vetores de posição dos metadados EPIC)",
    uncertainty="Metadados de efemérides da missão; a fonte não publica incerteza.",
    attribution="NASA EPIC Team / DSCOVR (epic.gsfc.nasa.gov)",
)


class _Xyz(Raw):
    x: float
    y: float
    z: float


class _Centroid(Raw):
    lat: float
    lon: float


class _EpicRaw(Raw):
    identifier: str
    image: str
    caption: str | None = None
    date: str
    centroid_coordinates: _Centroid
    dscovr_j2000_position: _Xyz
    lunar_j2000_position: _Xyz
    sun_j2000_position: _Xyz


class EpicImage(BaseModel):
    identifier: str
    caption: str | None
    observed_at: datetime
    centroid_lat_deg: float
    centroid_lon_deg: float
    dscovr_position_km: tuple[float, float, float]
    lunar_position_km: tuple[float, float, float]
    sun_position_km: tuple[float, float, float]
    image_png_url: str
    image_jpg_url: str
    thumbnail_url: str


def _xyz(v: _Xyz) -> tuple[float, float, float]:
    return (v.x, v.y, v.z)


def make_parser(base_url: str) -> Callable[[httpx.Response], Parsed[list[EpicImage]]]:
    def parse(resp: httpx.Response) -> Parsed[list[EpicImage]]:
        body = resp.json()
        if not isinstance(body, list):
            raise ValueError("EPIC: esperava uma lista de imagens")
        out = []
        for item in body:
            r = _EpicRaw.model_validate(item)
            t = parse_utc(r.date)
            if not r.image.replace("_", "").isalnum():
                raise ValueError("EPIC: nome de imagem inesperado")
            arch = f"{base_url}/archive/natural/{t:%Y/%m/%d}"
            out.append(
                EpicImage(
                    identifier=r.identifier,
                    caption=r.caption,
                    observed_at=t,
                    centroid_lat_deg=r.centroid_coordinates.lat,
                    centroid_lon_deg=r.centroid_coordinates.lon,
                    dscovr_position_km=_xyz(r.dscovr_j2000_position),
                    lunar_position_km=_xyz(r.lunar_j2000_position),
                    sun_position_km=_xyz(r.sun_j2000_position),
                    image_png_url=f"{arch}/png/{r.image}.png",
                    image_jpg_url=f"{arch}/jpg/{r.image}.jpg",
                    thumbnail_url=f"{arch}/thumbs/{r.image}.jpg",
                )
            )
        out.sort(key=lambda i: i.observed_at)
        if not out:
            return Parsed(out, notes=("Nenhuma imagem EPIC publicada para a data.",))
        return Parsed(
            out,
            observed_at=out[-1].observed_at,
            valid_time_start=out[0].observed_at,
            valid_time_end=out[-1].observed_at,
        )

    return parse


def fetch_epic(
    client: ExternalClient, settings: Settings, day: date | None
) -> SourceEnvelope[list[EpicImage]]:
    base = settings.epic_base_url
    path = f"/api/natural/date/{day.isoformat()}" if day else "/api/natural"
    return client.fetch(
        META,
        f"{base}{path}",
        cache_key=f"epic:{day or 'latest'}",
        ttl_s=settings.nasa_cache_ttl_seconds,
        parse=make_parser(base),
    )

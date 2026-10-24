"""NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information).

Endpoints usados (via api.nasa.gov): /DONKI/FLR, /DONKI/GST, /DONKI/CME, com
startDate/endDate (yyyy-MM-dd, UT). Docs: https://api.nasa.gov (seção DONKI) e
https://kauai.ccmc.gsfc.nasa.gov/DONKI/ (CCMC).
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.integrations.common import KM_M, HttpUrlStr, Raw
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient, Parsed, SourceMeta
from app.integrations.keys import nasa_key
from app.integrations.timeutil import day_end, day_start, parse_utc

MAX_DAYS = 30
ATTRIBUTION = "NASA CCMC DONKI (via api.nasa.gov)"


def _list_body(resp: httpx.Response) -> list[Any]:
    # Sem eventos no intervalo, o DONKI pode responder corpo vazio em vez de "[]".
    if not resp.content.strip():
        return []
    body = resp.json()
    if not isinstance(body, list):
        raise ValueError("DONKI: esperava uma lista de eventos")
    return body


# ---------- Erupções solares (FLR) ----------


class _FlrRaw(Raw):
    flrID: str  # noqa: N815 - nome do campo na fonte
    beginTime: str  # noqa: N815
    peakTime: str | None = None  # noqa: N815
    endTime: str | None = None  # noqa: N815
    classType: str | None = None  # noqa: N815
    sourceLocation: str | None = None  # noqa: N815
    activeRegionNum: int | None = None  # noqa: N815
    link: HttpUrlStr | None = None


class SolarFlare(BaseModel):
    id: str
    begin: datetime
    peak: datetime | None
    end: datetime | None
    class_type: str | None = Field(description="Classe GOES em raios X (A, B, C, M, X)")
    source_location: str | None = Field(description="Heliográfica, p. ex. S21W73")
    active_region: int | None
    link: str | None


def _parse_flr(resp: httpx.Response) -> list[SolarFlare]:
    out = []
    for item in _list_body(resp):
        r = _FlrRaw.model_validate(item)
        out.append(
            SolarFlare(
                id=r.flrID,
                begin=parse_utc(r.beginTime),
                peak=parse_utc(r.peakTime) if r.peakTime else None,
                end=parse_utc(r.endTime) if r.endTime else None,
                class_type=r.classType,
                source_location=r.sourceLocation,
                active_region=r.activeRegionNum,
                link=r.link,
            )
        )
    return sorted(out, key=lambda f: f.begin)


# ---------- Tempestades geomagnéticas (GST) ----------


class _KpRaw(Raw):
    observedTime: str  # noqa: N815
    kpIndex: float  # noqa: N815
    source: str


class _GstRaw(Raw):
    gstID: str  # noqa: N815
    startTime: str  # noqa: N815
    allKpIndex: list[_KpRaw] = Field(default_factory=list)  # noqa: N815
    link: HttpUrlStr | None = None


class KpObservation(BaseModel):
    observed_at: datetime
    kp: float
    source: str


class GeomagneticStorm(BaseModel):
    id: str
    start: datetime
    kp_max: float | None
    kp: list[KpObservation]
    link: str | None


def _parse_gst(resp: httpx.Response) -> list[GeomagneticStorm]:
    out = []
    for item in _list_body(resp):
        r = _GstRaw.model_validate(item)
        kp = [
            KpObservation(observed_at=parse_utc(k.observedTime), kp=k.kpIndex, source=k.source)
            for k in r.allKpIndex
        ]
        out.append(
            GeomagneticStorm(
                id=r.gstID,
                start=parse_utc(r.startTime),
                kp_max=max((k.kp for k in kp), default=None),
                kp=kp,
                link=r.link,
            )
        )
    return sorted(out, key=lambda g: g.start)


# ---------- Ejeções de massa coronal (CME) ----------


class _CmeAnalysisRaw(Raw):
    time21_5: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    halfAngle: float | None = None  # noqa: N815
    speed: float | None = None
    type: str | None = None
    isMostAccurate: bool = False  # noqa: N815


class _CmeRaw(Raw):
    activityID: str  # noqa: N815
    startTime: str  # noqa: N815
    sourceLocation: str | None = None  # noqa: N815
    note: str | None = None
    link: HttpUrlStr | None = None
    cmeAnalyses: list[_CmeAnalysisRaw] | None = None  # noqa: N815


class CmeAnalysis(BaseModel):
    time_21_5_rsun: datetime | None = Field(description="Instante em que cruza 21,5 raios solares")
    latitude_deg: float | None
    longitude_deg: float | None
    half_angle_deg: float | None
    speed_ms: float | None
    type: str | None


class CoronalMassEjection(BaseModel):
    id: str
    start: datetime
    source_location: str | None
    note: str | None
    analysis: CmeAnalysis | None = Field(description="Análise marcada como mais precisa")
    link: str | None


def _parse_cme(resp: httpx.Response) -> list[CoronalMassEjection]:
    out = []
    for item in _list_body(resp):
        r = _CmeRaw.model_validate(item)
        best = next((a for a in (r.cmeAnalyses or []) if a.isMostAccurate), None)
        analysis = (
            CmeAnalysis(
                time_21_5_rsun=parse_utc(best.time21_5) if best.time21_5 else None,
                latitude_deg=best.latitude,
                longitude_deg=best.longitude,
                half_angle_deg=best.halfAngle,
                speed_ms=best.speed * KM_M if best.speed is not None else None,
                type=best.type,
            )
            if best
            else None
        )
        out.append(
            CoronalMassEjection(
                id=r.activityID,
                start=parse_utc(r.startTime),
                source_location=r.sourceLocation,
                note=r.note,
                analysis=analysis,
                link=r.link,
            )
        )
    return sorted(out, key=lambda c: c.start)


# ---------- Busca ----------

_KINDS: dict[str, tuple[str, SourceMeta, Callable[[httpx.Response], list[Any]]]] = {
    "flares": (
        "FLR",
        SourceMeta(
            source="NASA DONKI FLR",
            units={"begin": "UTC", "peak": "UTC", "end": "UTC"},
            reference_frame="Coordenadas heliográficas (sourceLocation)",
            attribution=ATTRIBUTION,
        ),
        _parse_flr,
    ),
    "storms": (
        "GST",
        SourceMeta(
            source="NASA DONKI GST",
            units={"kp": "índice Kp (0-9, adimensional)", "start": "UTC"},
            reference_frame="Global (índice planetário Kp)",
            uncertainty="Kp é observacional; pode ser revisado pela fonte.",
            attribution=ATTRIBUTION,
        ),
        _parse_gst,
    ),
    "cmes": (
        "CME",
        SourceMeta(
            source="NASA DONKI CME",
            units={"speed_ms": "m/s", "half_angle_deg": "deg", "latitude_deg": "deg"},
            reference_frame="Heliográfica de Stonyhurst (análises CCMC/SWRC)",
            uncertainty="Velocidade e ângulo vêm da análise 'mais precisa' do catálogo, sem sigma.",
            attribution=ATTRIBUTION,
        ),
        _parse_cme,
    ),
}


def fetch_space_weather(
    client: ExternalClient, settings: Settings, start: date, end: date
) -> dict[str, SourceEnvelope[Any]]:
    """Consulta FLR, GST e CME em paralelo (o tempo total fica limitado a um timeout)."""
    if end < start or (end - start).days > MAX_DAYS:
        raise ValueError(f"Intervalo DONKI deve ter de 0 a {MAX_DAYS} dias.")
    key = nasa_key(settings)

    def one(kind: str) -> SourceEnvelope[Any]:
        path, base_meta, parse_list = _KINDS[kind]
        meta = replace(base_meta, notes=base_meta.notes + key.notes)
        if key.value is None:
            assert key.error is not None
            return ExternalClient.failed(meta, key.error)

        def parse(resp: httpx.Response) -> Parsed[list[Any]]:
            return Parsed(
                parse_list(resp), valid_time_start=day_start(start), valid_time_end=day_end(end)
            )

        return client.fetch(
            meta,
            f"{settings.nasa_api_base_url}/DONKI/{path}",
            params={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "api_key": key.value,
            },
            cache_key=f"donki:{path}:{start}:{end}",
            ttl_s=min(settings.nasa_cache_ttl_seconds, 900),
            parse=parse,
        )

    with ThreadPoolExecutor(max_workers=len(_KINDS)) as pool:
        results = dict(zip(_KINDS, pool.map(one, _KINDS), strict=True))
    return results

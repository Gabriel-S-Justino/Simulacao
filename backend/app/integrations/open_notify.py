"""Open Notify: posição atual da ISS (http://api.open-notify.org/iss-now.json).

Serviço comunitário (não é da NASA). O endpoint é HTTP; por isso é consumido só
pelo backend e nunca pelo navegador. Docs: https://open-notify-api.readthedocs.io
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.integrations.common import Raw
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient, Parsed, SourceFailure, SourceMeta

META = SourceMeta(
    source="Open Notify ISS",
    units={"lat_deg": "deg", "lon_deg": "deg", "observed_at": "UTC"},
    reference_frame="Subponto geográfico (latitude, longitude); datum não documentado",
    uncertainty="Sem incerteza publicada; sem altitude. Precisão limitada a exibição.",
    attribution="Open Notify (open-notify.org), dados derivados de elementos orbitais públicos",
    notes=("Serviço comunitário, não oficial da NASA.",),
)


class _Pos(Raw):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class _IssRaw(Raw):
    message: str
    timestamp: int
    iss_position: _Pos


class IssPosition(BaseModel):
    lat_deg: float
    lon_deg: float
    observed_at: datetime


def parse_iss(resp: httpx.Response) -> Parsed[IssPosition]:
    raw = _IssRaw.model_validate(resp.json())
    if raw.message != "success":
        raise SourceFailure("http_error", "Open Notify não reportou sucesso.", retryable=True)
    t = datetime.fromtimestamp(raw.timestamp, tz=UTC)
    return Parsed(
        IssPosition(
            lat_deg=raw.iss_position.latitude, lon_deg=raw.iss_position.longitude, observed_at=t
        ),
        observed_at=t,
    )


def fetch_iss(client: ExternalClient, settings: Settings) -> SourceEnvelope[IssPosition]:
    return client.fetch(
        META,
        f"{settings.open_notify_base_url}/iss-now.json",
        cache_key="iss-now",
        ttl_s=settings.iss_update_interval_seconds,
        parse=parse_iss,
        max_bytes=64 * 1024,
        # Posição da ISS envelhece rápido (~7,7 km/s): cópia antiga só por poucos minutos.
        max_stale_s=300,
    )

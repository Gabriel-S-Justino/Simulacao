"""Política de chave da api.nasa.gov (APOD, NeoWs, DONKI)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.integrations.envelope import SourceError

DEMO_KEY = "DEMO_KEY"


@dataclass(frozen=True)
class NasaKey:
    value: str | None
    notes: tuple[str, ...] = ()
    error: SourceError | None = None


def nasa_key(settings: Settings) -> NasaKey:
    key = (settings.nasa_api_key or "").strip()
    if key and key != DEMO_KEY:
        return NasaKey(key)
    if settings.is_production:
        return NasaKey(
            None,
            error=SourceError(
                code="not_configured",
                message="NASA_API_KEY ausente ou DEMO_KEY em produção; integração desativada.",
                retryable=False,
            ),
        )
    return NasaKey(
        DEMO_KEY,
        notes=(
            "Usando DEMO_KEY (apenas desenvolvimento): limite baixo de requisições. "
            "Configure NASA_API_KEY.",
        ),
    )

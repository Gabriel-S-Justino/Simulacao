"""Tipos auxiliares compartilhados pelos adaptadores."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

AU_M = 149_597_870_700.0  # IAU 2012, exato
KM_M = 1000.0


def _http_url(value: str) -> str:
    v = value.strip()
    if not v.lower().startswith(("https://", "http://")):
        raise ValueError("URL deve ser http(s)")
    return v


HttpUrlStr = Annotated[str, AfterValidator(_http_url)]
"""URL aceita para exibição no frontend (rejeita javascript:, data: etc.)."""


class Raw(BaseModel):
    """Base para payloads externos: ignora campos extras, exige os documentados."""

    model_config = ConfigDict(extra="ignore")

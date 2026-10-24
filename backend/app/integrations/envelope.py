"""Contrato comum (§4.9) para dados vindos de fontes externas.

Toda resposta de integração usa este envelope, com ou sem dados. Quando a fonte
falha e não há cópia em cache, ``data`` é ``None``: nada é inventado para
preencher o vazio.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceStatus = Literal["ok", "stale", "error", "not_configured"]
"""
- ok: dado obtido agora (ou em cache dentro do TTL).
- stale: a fonte falhou; servimos a última cópia válida, com ``stale=True`` e ``error``.
- error: a fonte falhou e não há cópia; ``data`` é ``None``.
- not_configured: falta configuração (p. ex. chave da NASA em produção); nada foi pedido.
"""

ErrorCode = Literal[
    "timeout",
    "connection",
    "http_error",
    "auth",
    "rate_limited",
    "not_found",
    "ambiguous",
    "invalid_payload",
    "not_configured",
]


class SourceError(BaseModel):
    code: ErrorCode
    message: str
    retryable: bool
    http_status: int | None = None
    # Usado por fontes que respondem "várias correspondências" (p. ex. SBDB, HTTP 300).
    candidates: list[str] = Field(default_factory=list)


class SourceEnvelope[T](BaseModel):
    source: str
    status: SourceStatus
    fetched_at: datetime | None
    observed_at: datetime | None = None
    valid_time_start: datetime | None = None
    valid_time_end: datetime | None = None
    stale: bool = False
    units: dict[str, str] = Field(default_factory=dict)
    reference_frame: str | None = None
    uncertainty: str | None = None
    data: T | None = None
    error: SourceError | None = None
    # Avisos de qualidade (p. ex. chave de demonstração em desenvolvimento, dado não oficial).
    notes: list[str] = Field(default_factory=list)
    attribution: str | None = None

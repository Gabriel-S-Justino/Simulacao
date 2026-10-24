"""Cliente HTTP comum das integrações: timeout, limite de tamanho, cache e "stale".

Regras:
- Erros nunca expõem a URL completa (pode conter ``api_key``); só o host e o caminho.
- Uma falha só é coberta por cache se a cópia tiver no máximo ``max_stale`` de idade,
  e a resposta sai marcada com ``status="stale"``, ``stale=True`` e o erro original.
- Respostas definitivas da fonte (não encontrado, ambíguo) não usam cópia antiga.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from pydantic import ValidationError

from app.integrations.envelope import ErrorCode, SourceEnvelope, SourceError

log = logging.getLogger("mission_architect.integrations")

_SECRET_QS = re.compile(r"(api_key=)[^&\s\"']+", re.IGNORECASE)


class _RedactSecrets(logging.Filter):
    """O logger do httpx registra a URL completa; remove o valor de ``api_key``."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "api_key=" in msg.lower():
            record.msg = _SECRET_QS.sub(r"\1***", msg)
            record.args = None
        return True


logging.getLogger("httpx").addFilter(_RedactSecrets())

USER_AGENT = "MissionArchitect/0.3 (+https://github.com/Gabriel-S-Justino/Simulacao)"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024


class SourceFailure(Exception):  # noqa: N818 - nome de domínio, não "Error" genérico
    """Falha reconhecida pelo adaptador (p. ex. objeto não encontrado)."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        http_status: int | None = None,
        candidates: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.error = SourceError(
            code=code,
            message=message,
            retryable=retryable,
            http_status=http_status,
            candidates=candidates or [],
        )


@dataclass(frozen=True)
class Parsed[T]:
    data: T
    observed_at: datetime | None = None
    valid_time_start: datetime | None = None
    valid_time_end: datetime | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceMeta:
    source: str
    units: Mapping[str, str] = field(default_factory=dict)
    reference_frame: str | None = None
    uncertainty: str | None = None
    attribution: str | None = None
    notes: tuple[str, ...] = ()


@dataclass
class _Entry:
    stored_at: datetime
    parsed: Parsed[Any]


class TTLCache:
    """Cache em memória por processo, limitado em entradas (LRU)."""

    def __init__(self, max_entries: int = 256) -> None:
        self._data: OrderedDict[str, _Entry] = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_entries

    def get(self, key: str) -> _Entry | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is not None:
                self._data.move_to_end(key)
            return entry

    def put(self, key: str, entry: _Entry) -> None:
        with self._lock:
            self._data[key] = entry
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def _status_failure(resp: httpx.Response) -> SourceFailure:
    code = resp.status_code
    if code in (401, 403):
        return SourceFailure("auth", f"Acesso negado pela fonte (HTTP {code}).", http_status=code)
    if code == 429:
        return SourceFailure(
            "rate_limited",
            "Limite de requisições da fonte atingido.",
            retryable=True,
            http_status=code,
        )
    if code == 404:
        return SourceFailure("not_found", "Recurso não encontrado na fonte.", http_status=code)
    return SourceFailure(
        "http_error", f"A fonte respondeu HTTP {code}.", retryable=code >= 500, http_status=code
    )


def _safe_target(url: str) -> str:
    u = httpx.URL(url)
    return f"{u.host}{u.path}"


class ExternalClient:
    def __init__(
        self,
        *,
        timeout_s: float = 10.0,
        max_stale_s: float = 7 * 24 * 3600,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._http = httpx.Client(
            timeout=httpx.Timeout(timeout_s),
            headers={"User-Agent": USER_AGENT},
            transport=transport,
            follow_redirects=True,
        )
        self.cache = TTLCache()
        self._max_stale = timedelta(seconds=max_stale_s)
        self._now = now

    def close(self) -> None:
        self._http.close()

    def fetch[T](
        self,
        meta: SourceMeta,
        url: str,
        *,
        params: Mapping[str, str | int | float] | None = None,
        cache_key: str,
        ttl_s: float,
        parse: Callable[[httpx.Response], Parsed[T]],
        accept_status: frozenset[int] = frozenset({200}),
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_stale_s: float | None = None,
    ) -> SourceEnvelope[T]:
        now = self._now()
        cached = self.cache.get(cache_key)
        if cached is not None and now - cached.stored_at <= timedelta(seconds=ttl_s):
            return self._envelope(meta, cached.parsed, cached.stored_at)

        try:
            resp = self._get(url, params, max_bytes)
            if resp.status_code not in accept_status:
                raise _status_failure(resp)
            parsed = parse(resp)
        except SourceFailure as exc:
            failure = exc.error
        except httpx.TimeoutException:
            failure = SourceError(code="timeout", message="Tempo esgotado.", retryable=True)
        except httpx.TransportError as exc:
            failure = SourceError(
                code="connection",
                message=f"Falha de conexão ({type(exc).__name__}).",
                retryable=True,
            )
        except (ValidationError, ValueError, KeyError, TypeError, IndexError) as exc:
            failure = SourceError(
                code="invalid_payload",
                message=f"Resposta fora do formato documentado ({type(exc).__name__}).",
                retryable=False,
            )
        else:
            self.cache.put(cache_key, _Entry(stored_at=now, parsed=parsed))
            return self._envelope(meta, parsed, now)

        log.warning(
            "external_source_failed",
            extra={
                "ctx": {
                    "source": meta.source,
                    "target": _safe_target(url),
                    "code": failure.code,
                    "http_status": failure.http_status,
                }
            },
        )
        definitive = failure.code in ("not_found", "ambiguous")
        max_stale = self._max_stale if max_stale_s is None else timedelta(seconds=max_stale_s)
        if cached is not None and not definitive and now - cached.stored_at <= max_stale:
            env = self._envelope(meta, cached.parsed, cached.stored_at)
            return env.model_copy(update={"status": "stale", "stale": True, "error": failure})
        return self.failed(meta, failure, fetched_at=now)

    def _get(
        self, url: str, params: Mapping[str, str | int | float] | None, max_bytes: int
    ) -> httpx.Response:
        with self._http.stream("GET", url, params=params) as resp:
            chunks: list[bytes] = []
            size = 0
            for chunk in resp.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise SourceFailure("invalid_payload", f"Resposta maior que {max_bytes} bytes.")
                chunks.append(chunk)
        # O corpo já foi descomprimido por iter_bytes; não repassar Content-Encoding.
        headers = {
            k: v
            for k, v in resp.headers.items()
            if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")
        }
        return httpx.Response(
            status_code=resp.status_code,
            headers=headers,
            content=b"".join(chunks),
            request=resp.request,
        )

    @staticmethod
    def failed[T](
        meta: SourceMeta, error: SourceError, fetched_at: datetime | None = None
    ) -> SourceEnvelope[T]:
        status = "not_configured" if error.code == "not_configured" else "error"
        return SourceEnvelope[T](
            source=meta.source,
            status=status,
            fetched_at=fetched_at,
            units=dict(meta.units),
            reference_frame=meta.reference_frame,
            uncertainty=meta.uncertainty,
            error=error,
            notes=list(meta.notes),
            attribution=meta.attribution,
        )

    @staticmethod
    def _envelope[T](
        meta: SourceMeta, parsed: Parsed[T], fetched_at: datetime
    ) -> SourceEnvelope[T]:
        return SourceEnvelope[T](
            source=meta.source,
            status="ok",
            fetched_at=fetched_at,
            observed_at=parsed.observed_at,
            valid_time_start=parsed.valid_time_start,
            valid_time_end=parsed.valid_time_end,
            stale=False,
            units=dict(meta.units),
            reference_frame=meta.reference_frame,
            uncertainty=meta.uncertainty,
            data=parsed.data,
            notes=[*meta.notes, *parsed.notes],
            attribution=meta.attribution,
        )

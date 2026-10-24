"""JPL Solar System Dynamics: Horizons (vetores), SBDB (elementos) e CAD (aproximações).

Docs:
- https://ssd-api.jpl.nasa.gov/doc/horizons.html
- https://ssd-api.jpl.nasa.gov/doc/sbdb.html
- https://ssd-api.jpl.nasa.gov/doc/cad.html

Instantes destas fontes estão em TDB (tempo dinâmico baricêntrico), não UTC; por isso
seguem como data juliana/texto TDB e não são convertidos sem tabela de segundos bissextos.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.integrations.common import AU_M, KM_M, Raw
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient, Parsed, SourceFailure, SourceMeta

ATTRIBUTION = "NASA/JPL Solar System Dynamics (ssd.jpl.nasa.gov)"

# ---------------------------------------------------------------- Horizons

HORIZONS_MAX_STEPS = 5000
_TARGET_RE = re.compile(r"^[A-Za-z0-9@;:.,\- ]{1,40}$")
_STEP_RE = re.compile(r"^(\d{1,5})\s?(m|h|d)$")
_STEP_SECONDS = {"m": 60, "h": 3600, "d": 86400}

HORIZONS_META = SourceMeta(
    source="JPL Horizons",
    units={"r_m": "m", "v_ms": "m/s", "jd_tdb": "dia juliano (TDB)"},
    reference_frame=(
        "ICRF, plano do equador (REF_PLANE=FRAME), origem dada por 'center' (500@399 = geocentro)"
    ),
    uncertainty=(
        "Efeméride nominal do JPL; incertezas por objeto não vêm nesta tabela "
        "(consultar SBDB para pequenos corpos)."
    ),
    attribution=ATTRIBUTION,
)


class StateVector(BaseModel):
    jd_tdb: float
    calendar_tdb: str
    r_m: tuple[float, float, float]
    v_ms: tuple[float, float, float]


class HorizonsVectors(BaseModel):
    target: str
    target_name: str | None
    center: str
    time_scale: str = "TDB"
    start_tdb: str
    stop_tdb: str
    step: str
    states: list[StateVector]


class _HorizonsRaw(Raw):
    result: str | None = None
    error: str | None = None


def validate_horizons_request(target: str, center: str, step: str, span_s: float) -> None:
    for name, value in (("target", target), ("center", center)):
        if not _TARGET_RE.match(value):
            raise ValueError(f"'{name}' contém caracteres não aceitos.")
    m = _STEP_RE.match(step.strip())
    if not m:
        raise ValueError("'step' deve ser como '10 m', '1 h' ou '1 d'.")
    step_s = int(m.group(1)) * _STEP_SECONDS[m.group(2)]
    if step_s <= 0:
        raise ValueError("'step' deve ser positivo.")
    if span_s <= 0:
        raise ValueError("'stop' deve ser posterior a 'start'.")
    if span_s / step_s > HORIZONS_MAX_STEPS:
        raise ValueError(f"No máximo {HORIZONS_MAX_STEPS} amostras por consulta.")


def parse_horizons_result(text: str) -> tuple[str | None, list[StateVector]]:
    if "$$SOE" not in text:
        low = text.lower()
        if "multiple" in low and "match" in low:
            raise SourceFailure("ambiguous", "Alvo ambíguo no Horizons; use o ID numérico.")
        if "no matches found" in low or "no such" in low or "unknown" in low:
            raise SourceFailure("not_found", "Alvo não encontrado no Horizons.")
        raise ValueError("Horizons: tabela $$SOE/$$EOE ausente")
    head, _, rest = text.partition("$$SOE")
    body, sep, _ = rest.partition("$$EOE")
    if not sep:
        raise ValueError("Horizons: $$EOE ausente")
    header = next(
        (ln for ln in reversed(head.splitlines()) if ln.strip().startswith("JDTDB")), None
    )
    if header is None:
        raise ValueError("Horizons: cabeçalho CSV ausente (esperava CSV_FORMAT=YES)")
    cols = [c.strip() for c in header.split(",")]
    idx = {name: cols.index(name) for name in ("JDTDB", "X", "Y", "Z", "VX", "VY", "VZ")}
    cal = next((i for i, c in enumerate(cols) if c.startswith("Calendar Date")), None)
    states = []
    for line in body.strip().splitlines():
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split(",")]
        states.append(
            StateVector(
                jd_tdb=float(cells[idx["JDTDB"]]),
                calendar_tdb=cells[cal] if cal is not None else "",
                r_m=(
                    float(cells[idx["X"]]) * KM_M,
                    float(cells[idx["Y"]]) * KM_M,
                    float(cells[idx["Z"]]) * KM_M,
                ),
                v_ms=(
                    float(cells[idx["VX"]]) * KM_M,
                    float(cells[idx["VY"]]) * KM_M,
                    float(cells[idx["VZ"]]) * KM_M,
                ),
            )
        )
    if not states:
        raise ValueError("Horizons: tabela vazia")
    name = re.search(r"Target body name:\s*(.+?)\s{2,}", head)
    return (name.group(1).strip() if name else None), states


def fetch_horizons_vectors(
    client: ExternalClient,
    settings: Settings,
    *,
    target: str,
    center: str,
    start: datetime,
    stop: datetime,
    step: str,
) -> SourceEnvelope[HorizonsVectors]:
    validate_horizons_request(target, center, step, (stop - start).total_seconds())
    start_s, stop_s = f"{start:%Y-%m-%d %H:%M}", f"{stop:%Y-%m-%d %H:%M}"

    def parse(resp: httpx.Response) -> Parsed[HorizonsVectors]:
        raw = _HorizonsRaw.model_validate(resp.json())
        if raw.error:
            raise SourceFailure("http_error", f"Horizons recusou a consulta: {raw.error[:200]}")
        if raw.result is None:
            raise ValueError("Horizons: campo 'result' ausente")
        name, states = parse_horizons_result(raw.result)
        return Parsed(
            HorizonsVectors(
                target=target,
                target_name=name,
                center=center,
                start_tdb=start_s,
                stop_tdb=stop_s,
                step=step,
                states=states,
            ),
            notes=("Instantes em TDB (TDB - UTC ≈ 69 s em 2024).",),
        )

    def q(v: str) -> str:
        return f"'{v}'"  # Horizons exige valores entre aspas simples

    return client.fetch(
        HORIZONS_META,
        settings.jpl_horizons_base_url,
        params={
            "format": "json",
            "COMMAND": q(target),
            "OBJ_DATA": "'NO'",
            "MAKE_EPHEM": "'YES'",
            "EPHEM_TYPE": "'VECTORS'",
            "CENTER": q(center),
            "START_TIME": q(start_s),
            "STOP_TIME": q(stop_s),
            "STEP_SIZE": q(step),
            "VEC_TABLE": "'2'",
            "REF_PLANE": "'FRAME'",
            "REF_SYSTEM": "'ICRF'",
            "OUT_UNITS": "'KM-S'",
            "CSV_FORMAT": "'YES'",
            "VEC_LABELS": "'NO'",
        },
        cache_key=f"horizons:{target}:{center}:{start_s}:{stop_s}:{step}",
        ttl_s=24 * 3600,
        parse=parse,
        max_bytes=8 * 1024 * 1024,
    )


# ---------------------------------------------------------------- SBDB

SBDB_META = SourceMeta(
    source="JPL SBDB",
    units={
        "a": "m",
        "q": "m",
        "ad": "m",
        "moid_m": "m",
        "e": "1",
        "i": "deg",
        "om": "deg",
        "w": "deg",
        "ma": "deg",
        "tp": "dia juliano (TDB)",
        "per": "d",
        "n": "deg/d",
    },
    reference_frame="Heliocêntrico, eclíptica e equinócio J2000",
    uncertainty="sigma de cada elemento conforme a solução orbital do JPL (1-sigma)",
    attribution=ATTRIBUTION,
)

_AU_ELEMENTS = {"a", "q", "ad"}


class _SbdbElement(Raw):
    name: str
    title: str | None = None
    value: float | None
    sigma: float | None = None
    units: str | None = None


class _SbdbOrbit(Raw):
    epoch: float
    elements: list[_SbdbElement]
    moid: float | None = None
    condition_code: str | None = None
    first_obs: str | None = None
    last_obs: str | None = None
    equinox: str | None = None


class _OrbitClass(Raw):
    name: str
    code: str | None = None


class _SbdbObject(Raw):
    des: str
    fullname: str
    spkid: str | None = None
    kind: str | None = None
    neo: bool = False
    pha: bool = False
    orbit_class: _OrbitClass | None = None


class _SbdbRaw(Raw):
    object: _SbdbObject
    orbit: _SbdbOrbit


class OrbitalElement(BaseModel):
    name: str
    title: str | None
    value: float
    sigma: float | None
    units: str | None


class SmallBody(BaseModel):
    designation: str
    full_name: str
    spkid: str | None
    kind: str | None
    neo: bool
    pha: bool
    orbit_class: str | None
    epoch_jd_tdb: float
    elements: list[OrbitalElement]
    moid_m: float | None
    condition_code: str | None
    first_obs: str | None
    last_obs: str | None


def parse_sbdb(resp: httpx.Response) -> Parsed[SmallBody]:
    body: dict[str, Any] = resp.json()
    if resp.status_code == 300 or body.get("code") in (300, "300"):
        cands = [f"{c.get('pdes')} {c.get('name') or ''}".strip() for c in body.get("list", [])]
        raise SourceFailure(
            "ambiguous", "A busca corresponde a mais de um objeto.", candidates=cands[:20]
        )
    if "object" not in body:
        raise SourceFailure("not_found", "Objeto não encontrado no SBDB.")
    raw = _SbdbRaw.model_validate(body)
    elements = []
    for el in raw.orbit.elements:
        if el.value is None:
            continue
        k = AU_M if el.name in _AU_ELEMENTS else 1.0
        elements.append(
            OrbitalElement(
                name=el.name,
                title=el.title,
                value=el.value * k,
                sigma=el.sigma * k if el.sigma is not None else None,
                units="m" if el.name in _AU_ELEMENTS else el.units,
            )
        )
    o = raw.object
    return Parsed(
        SmallBody(
            designation=o.des,
            full_name=o.fullname.strip(),
            spkid=o.spkid,
            kind=o.kind,
            neo=o.neo,
            pha=o.pha,
            orbit_class=o.orbit_class.name if o.orbit_class else None,
            epoch_jd_tdb=raw.orbit.epoch,
            elements=elements,
            moid_m=raw.orbit.moid * AU_M if raw.orbit.moid is not None else None,
            condition_code=raw.orbit.condition_code,
            first_obs=raw.orbit.first_obs,
            last_obs=raw.orbit.last_obs,
        ),
        notes=("Consulta com full-prec=true (precisão completa da solução).",),
    )


def fetch_small_body(
    client: ExternalClient, settings: Settings, query: str
) -> SourceEnvelope[SmallBody]:
    q = query.strip()
    if not _TARGET_RE.match(q):
        raise ValueError("Busca contém caracteres não aceitos.")
    return client.fetch(
        SBDB_META,
        f"{settings.jpl_ssd_api_base_url}/sbdb.api",
        params={"sstr": q, "full-prec": "true"},
        cache_key=f"sbdb:{q.lower()}",
        ttl_s=24 * 3600,
        parse=parse_sbdb,
        accept_status=frozenset({200, 300}),
    )


# ---------------------------------------------------------------- CAD

CAD_META = SourceMeta(
    source="JPL SBDB Close-Approach Data (CNEOS)",
    units={
        "distance_m": "m",
        "distance_min_m": "m",
        "distance_max_m": "m",
        "v_rel_ms": "m/s",
        "v_inf_ms": "m/s",
        "h_mag": "mag",
        "diameter_m": "m",
        "jd_tdb": "dia juliano (TDB)",
    },
    reference_frame="Distância ao centro do corpo de aproximação (padrão: Terra)",
    uncertainty="distance_min/max = faixa 3-sigma; t_sigma = incerteza 3-sigma do instante",
    attribution="NASA/JPL CNEOS - SBDB Close-Approach Data API",
)


class CloseApproach(BaseModel):
    designation: str
    full_name: str | None
    orbit_id: str
    jd_tdb: float
    calendar_tdb: str
    distance_m: float
    distance_min_m: float
    distance_max_m: float
    v_rel_ms: float
    v_inf_ms: float | None
    t_sigma: str
    h_mag: float | None
    diameter_m: float | None
    diameter_sigma_m: float | None


class _CadRaw(Raw):
    count: int
    fields: list[str] = Field(default_factory=list)
    data: list[list[str | float | None]] = Field(default_factory=list)


def _f(v: object) -> float | None:
    return None if v is None or v == "" else float(v)  # type: ignore[arg-type]


def _km(v: float | None) -> float | None:
    return None if v is None else v * KM_M


def _req_f(v: object) -> float:
    x = _f(v)
    if x is None:
        raise ValueError("CAD: valor obrigatório ausente")
    return x


def parse_cad(resp: httpx.Response) -> Parsed[list[CloseApproach]]:
    raw = _CadRaw.model_validate(resp.json())
    if raw.count == 0:
        return Parsed([])
    pos = {name: i for i, name in enumerate(raw.fields)}
    for needed in (
        "des",
        "orbit_id",
        "jd",
        "cd",
        "dist",
        "dist_min",
        "dist_max",
        "v_rel",
        "t_sigma_f",
    ):
        if needed not in pos:
            raise ValueError(f"CAD: campo '{needed}' ausente")

    def col(row: list[str | float | None], name: str) -> object:
        return row[pos[name]] if name in pos else None

    out = []
    for row in raw.data:
        name = col(row, "fullname")
        out.append(
            CloseApproach(
                designation=str(col(row, "des")),
                full_name=str(name).strip() if name else None,
                orbit_id=str(col(row, "orbit_id")),
                jd_tdb=_req_f(col(row, "jd")),
                calendar_tdb=str(col(row, "cd")),
                distance_m=_req_f(col(row, "dist")) * AU_M,
                distance_min_m=_req_f(col(row, "dist_min")) * AU_M,
                distance_max_m=_req_f(col(row, "dist_max")) * AU_M,
                v_rel_ms=_req_f(col(row, "v_rel")) * KM_M,
                v_inf_ms=_km(_f(col(row, "v_inf"))),
                t_sigma=str(col(row, "t_sigma_f")),
                h_mag=_f(col(row, "h")),
                diameter_m=_km(_f(col(row, "diameter"))),
                diameter_sigma_m=_km(_f(col(row, "diameter_sigma"))),
            )
        )
    return Parsed(out, notes=("Instantes em TDB.",))


def fetch_close_approaches(
    client: ExternalClient, settings: Settings, *, days: int, dist_max_au: float
) -> SourceEnvelope[list[CloseApproach]]:
    return client.fetch(
        CAD_META,
        f"{settings.jpl_ssd_api_base_url}/cad.api",
        params={
            "date-min": "now",
            "date-max": f"+{days}",
            "dist-max": f"{dist_max_au:g}",
            "sort": "date",
            "diameter": "true",
            "fullname": "true",
        },
        cache_key=f"cad:{days}:{dist_max_au:g}",
        ttl_s=min(settings.nasa_cache_ttl_seconds, 6 * 3600),
        parse=parse_cad,
    )

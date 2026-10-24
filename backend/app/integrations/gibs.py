"""NASA GIBS: disponibilidade e datas das camadas usadas pela Terra 3D.

Lê o WMTS GetCapabilities (EPSG:4326, "best") e extrai, só para as camadas
configuradas, título, formatos e a dimensão de tempo (Default e Value). As imagens
continuam sendo baixadas pelo navegador direto da GIBS (serviço público, sem chave).
Docs: https://nasa-gibs.github.io/gibs-api-docs/access-basics/
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import date

import httpx
from pydantic import BaseModel

from app.core.config import Settings
from app.integrations.envelope import SourceEnvelope
from app.integrations.http import ExternalClient, Parsed, SourceMeta

WMTS = "{http://www.opengis.net/wmts/1.0}"
OWS = "{http://www.opengis.net/ows/1.1}"

LAYERS = (
    "BlueMarble_ShadedRelief_Bathymetry",
    "VIIRS_Black_Marble",
    "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    "MODIS_Terra_CorrectedReflectance_TrueColor",
)

META = SourceMeta(
    source="NASA GIBS",
    units={"latest_date": "data UTC (YYYY-MM-DD)"},
    reference_frame="EPSG:4326 (geográfica, equiretangular)",
    uncertainty="Imagens de visualização (não radiometria calibrada).",
    attribution=(
        "We acknowledge the use of imagery provided by services from NASA's Global "
        "Imagery Browse Services (GIBS), part of NASA's Earth Science Data and "
        "Information System (ESDIS)."
    ),
    notes=("O GetCapabilities lista só os 100 períodos mais recentes de cada camada.",),
)


class GibsLayerInfo(BaseModel):
    id: str
    title: str
    formats: list[str]
    tile_matrix_sets: list[str]
    time_default: str | None
    time_values: list[str]
    latest_date: date | None


class GibsCatalog(BaseModel):
    wms_endpoint: str
    layers: list[GibsLayerInfo]
    missing: list[str]


def _latest(values: list[str], default: str | None) -> date | None:
    for v in reversed(values):
        parts = v.split("/")
        end = parts[1] if len(parts) == 3 else parts[0]
        try:
            return date.fromisoformat(end[:10])
        except ValueError:
            continue
    if default:
        try:
            return date.fromisoformat(default[:10])
        except ValueError:
            return None
    return None


def _layer(el: ET.Element) -> GibsLayerInfo:
    ident = el.findtext(f"{OWS}Identifier") or ""
    time_default: str | None = None
    values: list[str] = []
    for dim in el.findall(f"{WMTS}Dimension"):
        if (dim.findtext(f"{OWS}Identifier") or "").lower() == "time":
            time_default = dim.findtext(f"{WMTS}Default")
            values = [v.text.strip() for v in dim.findall(f"{WMTS}Value") if v.text]
    return GibsLayerInfo(
        id=ident,
        title=el.findtext(f"{OWS}Title") or ident,
        formats=[f.text for f in el.findall(f"{WMTS}Format") if f.text],
        tile_matrix_sets=[
            t.text for t in el.findall(f"{WMTS}TileMatrixSetLink/{WMTS}TileMatrixSet") if t.text
        ],
        time_default=time_default,
        time_values=values,
        latest_date=_latest(values, time_default),
    )


def make_parser(base_url: str) -> Callable[[httpx.Response], Parsed[GibsCatalog]]:
    def parse(resp: httpx.Response) -> Parsed[GibsCatalog]:
        wanted = set(LAYERS)
        found: dict[str, GibsLayerInfo] = {}
        saw_contents = False
        for _event, el in ET.iterparse(io.BytesIO(resp.content), events=("end",)):
            if el.tag == f"{WMTS}Layer":
                ident = el.findtext(f"{OWS}Identifier")
                if ident in wanted:
                    found[ident] = _layer(el)
                el.clear()
            elif el.tag == f"{WMTS}TileMatrixSet" and len(el):
                el.clear()
            elif el.tag == f"{WMTS}Contents":
                saw_contents = True
        if not saw_contents:
            raise ValueError("GIBS: documento sem wmts:Contents")
        layers = [found[i] for i in LAYERS if i in found]
        return Parsed(
            GibsCatalog(
                wms_endpoint=f"{base_url}/wms/epsg4326/best/wms.cgi",
                layers=layers,
                missing=[i for i in LAYERS if i not in found],
            )
        )

    return parse


def fetch_layers(client: ExternalClient, settings: Settings) -> SourceEnvelope[GibsCatalog]:
    base = settings.gibs_base_url
    return client.fetch(
        META,
        f"{base}/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml",
        cache_key="gibs:capabilities",
        ttl_s=6 * 3600,
        parse=make_parser(base),
        max_bytes=64 * 1024 * 1024,
    )

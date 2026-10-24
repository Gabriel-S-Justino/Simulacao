"""Testes isolados das integrações externas (sem rede: httpx.MockTransport).

As respostas vêm de app/tests/external_fixtures.py, montadas a partir da
documentação oficial (não são gravações ao vivo).
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.v1.sources import get_external_client
from app.core.config import Settings, get_settings
from app.integrations import apod, donki, eonet, epic, gibs, jpl, neows, open_notify
from app.integrations.http import ExternalClient, Parsed, SourceMeta
from app.main import app
from app.tests import external_fixtures as fx

Handler = Callable[[httpx.Request], httpx.Response]
META = SourceMeta(source="Teste", units={"x": "m"})


class Clock:
    def __init__(self) -> None:
        self.t = datetime(2024, 5, 10, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += timedelta(seconds=seconds)


def make_client(handler: Handler, clock: Clock | None = None) -> ExternalClient:
    return ExternalClient(
        transport=httpx.MockTransport(handler),
        now=clock or Clock(),
        max_stale_s=3600,
    )


def settings(**kw: Any) -> Settings:
    base: dict[str, Any] = {"app_env": "development", "nasa_api_key": "TESTKEY"}
    base.update(kw)
    return Settings(**base)


def json_handler(body: Any, status: int = 200) -> Handler:
    return lambda _req: httpx.Response(status, json=body)


def parse_x(resp: httpx.Response) -> Parsed[float]:
    return Parsed(float(resp.json()["x"]))


def fetch_x(client: ExternalClient, **kw: Any) -> Any:
    return client.fetch(
        META,
        "https://example.test/x",
        params={"api_key": "SEGREDO"},
        cache_key="x",
        ttl_s=60,
        parse=parse_x,
        **kw,
    )


# ------------------------------------------------------------ cliente comum


def test_ok_envelope_fields() -> None:
    clock = Clock()
    env = fetch_x(make_client(json_handler({"x": 1.5}), clock))
    assert env.status == "ok"
    assert env.data == 1.5
    assert env.stale is False and env.error is None
    assert env.fetched_at == clock.t
    assert env.units == {"x": "m"}


def test_cache_within_ttl_avoids_request() -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(200, json={"x": 2})

    clock = Clock()
    client = make_client(handler, clock)
    fetch_x(client)
    clock.advance(30)
    env = fetch_x(client)
    assert len(calls) == 1
    assert env.status == "ok" and env.fetched_at == clock.t - timedelta(seconds=30)
    clock.advance(31)
    fetch_x(client)
    assert len(calls) == 2


def test_timeout() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lento", request=req)

    env = fetch_x(make_client(handler))
    assert env.status == "error" and env.data is None
    assert env.error.code == "timeout" and env.error.retryable


def test_connection_failure() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusado", request=req)

    env = fetch_x(make_client(handler))
    assert env.error.code == "connection" and env.data is None


@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [
        (401, "auth", False),
        (403, "auth", False),
        (404, "not_found", False),
        (429, "rate_limited", True),
        (500, "http_error", True),
        (503, "http_error", True),
        (400, "http_error", False),
    ],
)
def test_http_errors(status: int, code: str, retryable: bool) -> None:
    env = fetch_x(make_client(json_handler({"erro": 1}, status)))
    assert env.status == "error"
    assert env.error.code == code
    assert env.error.retryable is retryable
    assert env.error.http_status == status


def test_invalid_payload() -> None:
    env = fetch_x(make_client(json_handler({"y": 1})))
    assert env.error.code == "invalid_payload" and env.data is None
    env = fetch_x(make_client(lambda _r: httpx.Response(200, content=b"<html>")))
    assert env.error.code == "invalid_payload"


def test_stale_served_on_failure_with_original_error() -> None:
    state = {"fail": False}

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(503) if state["fail"] else httpx.Response(200, json={"x": 7})

    clock = Clock()
    client = make_client(handler, clock)
    first = fetch_x(client)
    state["fail"] = True
    clock.advance(120)
    env = fetch_x(client)
    assert env.status == "stale" and env.stale is True
    assert env.data == 7
    assert env.fetched_at == first.fetched_at
    assert env.error.code == "http_error"


def test_stale_too_old_is_not_served() -> None:
    state = {"fail": False}

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(503) if state["fail"] else httpx.Response(200, json={"x": 7})

    clock = Clock()
    client = make_client(handler, clock)
    fetch_x(client)
    state["fail"] = True
    clock.advance(3601)
    env = fetch_x(client)
    assert env.status == "error" and env.data is None
    clock.advance(-3601 + 120)
    assert fetch_x(client, max_stale_s=60).status == "error"


def test_not_found_never_uses_stale_copy() -> None:
    state = {"status": 200}
    clock = Clock()
    client = make_client(lambda _r: httpx.Response(state["status"], json={"x": 1}), clock)
    fetch_x(client)
    state["status"] = 404
    clock.advance(120)
    env = fetch_x(client)
    assert env.status == "error" and env.data is None


def test_api_key_sent_but_never_echoed(caplog: pytest.LogCaptureFixture) -> None:
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.url.params.get("api_key"))
        return httpx.Response(500)

    env = fetch_x(make_client(handler))
    assert seen == ["SEGREDO"]
    assert "SEGREDO" not in env.model_dump_json()
    assert "SEGREDO" not in caplog.text
    assert "api_key=***" in caplog.text


def test_oversized_response_rejected() -> None:
    env = fetch_x(make_client(json_handler({"x": 1, "pad": "a" * 5000})), max_bytes=1000)
    assert env.error.code == "invalid_payload"


def test_gzip_body_is_decoded_once() -> None:
    body = gzip.compress(json.dumps({"x": 3}).encode())

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"Content-Encoding": "gzip"})

    assert fetch_x(make_client(handler)).data == 3


# ------------------------------------------------------------ chave da NASA


def test_production_without_key_makes_no_request() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria chamar a rede")

    client = make_client(handler)
    for key in (None, "", "DEMO_KEY"):
        env = apod.fetch_apod(client, settings(app_env="production", nasa_api_key=key), None)
        assert env.status == "not_configured" and env.error.code == "not_configured"


def test_development_without_key_uses_demo_key_with_note() -> None:
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.url.params["api_key"])
        return httpx.Response(200, json=fx.APOD)

    env = apod.fetch_apod(make_client(handler), settings(nasa_api_key=None), None)
    assert seen == ["DEMO_KEY"]
    assert any("DEMO_KEY" in n for n in env.notes)


# ------------------------------------------------------------ adaptadores


def test_apod() -> None:
    env = apod.fetch_apod(make_client(json_handler(fx.APOD)), settings(), date(2024, 5, 10))
    assert env.status == "ok"
    assert env.data.page_url == "https://apod.nasa.gov/apod/ap240510.html"
    assert env.valid_time_start == datetime(2024, 5, 10, tzinfo=UTC)


def test_apod_rejects_non_http_media_url() -> None:
    bad = {**fx.APOD, "url": "javascript:alert(1)"}
    env = apod.fetch_apod(make_client(json_handler(bad)), settings(), None)
    assert env.error.code == "invalid_payload"


def test_neows_converts_strings_and_units() -> None:
    env = neows.fetch_feed(
        make_client(json_handler(fx.NEOWS_FEED)), settings(), date(2024, 5, 10), date(2024, 5, 11)
    )
    a = env.data.approaches[0]
    assert a.miss_distance_m == pytest.approx(2_991_957_400.0)
    assert a.relative_velocity_ms == pytest.approx(10_500.0)
    assert a.diameter_min_m == 100.0
    assert a.close_approach_epoch == datetime(2024, 5, 10, 12, 0, tzinfo=UTC)


def test_neows_range_limit() -> None:
    with pytest.raises(ValueError):
        neows.fetch_feed(
            make_client(json_handler({})), settings(), date(2024, 5, 1), date(2024, 5, 8)
        )


def test_donki_space_weather() -> None:
    bodies = {"FLR": fx.DONKI_FLR, "GST": fx.DONKI_GST, "CME": fx.DONKI_CME}

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bodies[req.url.path.rsplit("/", 1)[-1]])

    out = donki.fetch_space_weather(
        make_client(handler), settings(), date(2024, 5, 9), date(2024, 5, 11)
    )
    flare = out["flares"].data[0]
    assert flare.class_type == "X3.9"
    assert flare.peak == datetime(2024, 5, 10, 6, 54, tzinfo=UTC)
    assert out["storms"].data[0].kp_max == 9.0
    cme = out["cmes"].data[0]
    assert cme.analysis is not None and cme.analysis.speed_ms == 1_200_000.0


def test_donki_empty_body_means_no_events() -> None:
    out = donki.fetch_space_weather(
        make_client(lambda _r: httpx.Response(200, content=b"")),
        settings(),
        date(2024, 5, 9),
        date(2024, 5, 11),
    )
    assert all(env.status == "ok" and env.data == [] for env in out.values())


def test_epic_builds_archive_urls() -> None:
    env = epic.fetch_epic(make_client(json_handler(fx.EPIC)), settings(), None)
    img = env.data[-1]
    assert img.image_png_url == (
        "https://epic.gsfc.nasa.gov/archive/natural/2024/05/10/png/epic_1b_20240510014136.png"
    )
    assert img.thumbnail_url.endswith("/thumbs/epic_1b_20240510014136.jpg")
    assert env.observed_at == datetime(2024, 5, 10, 1, 36, 48, tzinfo=UTC)


def test_epic_rejects_unexpected_image_name() -> None:
    bad = [{**fx.EPIC[0], "image": "../../etc"}]
    env = epic.fetch_epic(make_client(json_handler(bad)), settings(), None)
    assert env.error.code == "invalid_payload"


def test_eonet_points_and_polygons() -> None:
    env = eonet.fetch_events(make_client(json_handler(fx.EONET)), settings(), days=30, limit=10)
    storm, fire = env.data
    assert storm.geometry[-1].lon_deg == 129.0 and storm.geometry[-1].point_method == "point"
    assert storm.geometry[-1].magnitude_unit == "kts"
    g = fire.geometry[0]
    assert g.point_method == "polygon_vertex_mean"
    assert (g.lon_deg, g.lat_deg) == (-119.5, 40.5)
    assert any("oficial" in n for n in env.notes)


def test_eonet_rejects_out_of_range_coordinates() -> None:
    bad = json.loads(json.dumps(fx.EONET))
    bad["events"][0]["geometry"][0]["coordinates"] = [200.0, 12.0]
    env = eonet.fetch_events(make_client(json_handler(bad)), settings(), days=30, limit=10)
    assert env.error.code == "invalid_payload"


def test_iss_position() -> None:
    env = open_notify.fetch_iss(make_client(json_handler(fx.ISS)), settings())
    assert env.data.lat_deg == pytest.approx(-19.783929798887073)
    assert env.observed_at == datetime.fromtimestamp(1454357342, tz=UTC)


def test_iss_failure_message() -> None:
    env = open_notify.fetch_iss(
        make_client(json_handler({**fx.ISS, "message": "fail"})), settings()
    )
    assert env.status == "error"


def test_horizons_vectors_parsed_in_si() -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"signature": {}, "result": fx.HORIZONS_RESULT})

    env = jpl.fetch_horizons_vectors(
        make_client(handler),
        settings(),
        target="301",
        center="500@399",
        start=datetime(2024, 5, 10),
        stop=datetime(2024, 5, 10, 1),
        step="1 h",
    )
    assert seen[0].url.params["REF_PLANE"] == "'FRAME'"
    assert seen[0].url.params["CSV_FORMAT"] == "'YES'"
    s0 = env.data.states[0]
    assert s0.r_m == (3.0e8, 2.0e8, 1.0e8)
    assert s0.v_ms == pytest.approx((-500.0, 600.0, 300.0))
    assert s0.jd_tdb == 2460440.5
    assert env.data.target_name == "Moon (301)"
    assert len(env.data.states) == 2


def test_horizons_errors() -> None:
    with pytest.raises(ValueError):
        jpl.validate_horizons_request("301'", "500@399", "1 h", 3600)
    with pytest.raises(ValueError):
        jpl.validate_horizons_request("301", "500@399", "1 m", 86400 * 10)
    with pytest.raises(ValueError):
        jpl.parse_horizons_result("sem tabela")
    multi = 'Multiple major-bodies match string "Mars"'
    from app.integrations.http import SourceFailure

    with pytest.raises(SourceFailure) as e:
        jpl.parse_horizons_result(multi)
    assert e.value.error.code == "ambiguous"


def test_sbdb_ok_converts_au() -> None:
    env = jpl.fetch_small_body(make_client(json_handler(fx.SBDB_OK)), settings(), "Eros")
    els = {e.name: e for e in env.data.elements}
    assert els["a"].value == pytest.approx(1.458 * 149_597_870_700.0)
    assert els["a"].units == "m"
    assert els["i"].units == "deg" and els["e"].sigma == pytest.approx(1e-9)
    assert env.data.moid_m == pytest.approx(0.15 * 149_597_870_700.0)


def test_sbdb_ambiguous_and_not_found() -> None:
    env = jpl.fetch_small_body(make_client(json_handler(fx.SBDB_MULTI, 300)), settings(), "1P")
    assert env.error.code == "ambiguous"
    assert env.error.candidates[0] == "1P 1P/Halley"
    nf = {"signature": {}, "message": "specified object was not found"}
    env = jpl.fetch_small_body(make_client(json_handler(nf)), settings(), "xyz")
    assert env.error.code == "not_found"


def test_cad_rows_and_empty() -> None:
    env = jpl.fetch_close_approaches(
        make_client(json_handler(fx.CAD)), settings(), days=30, dist_max_au=0.05
    )
    ca = env.data[0]
    assert ca.distance_m == pytest.approx(0.01 * 149_597_870_700.0)
    assert ca.v_rel_ms == pytest.approx(8500.0)
    assert ca.diameter_m is None and ca.full_name == "(2099 XX1)"
    empty = {"signature": {}, "count": 0}
    env = jpl.fetch_close_approaches(
        make_client(json_handler(empty)), settings(), days=30, dist_max_au=0.05
    )
    assert env.status == "ok" and env.data == []


def test_gibs_capabilities() -> None:
    client = make_client(lambda _r: httpx.Response(200, content=fx.GIBS_CAPABILITIES))
    env = gibs.fetch_layers(client, settings())
    by_id = {layer.id: layer for layer in env.data.layers}
    viirs = by_id["VIIRS_SNPP_CorrectedReflectance_TrueColor"]
    assert viirs.latest_date == date(2024, 5, 10)
    assert viirs.time_default == "2024-05-10"
    assert by_id["BlueMarble_ShadedRelief_Bathymetry"].latest_date is None
    assert "Unrelated_Layer" not in by_id
    assert set(env.data.missing) == {
        "VIIRS_Black_Marble",
        "MODIS_Terra_CorrectedReflectance_TrueColor",
    }


# ------------------------------------------------------------ rotas


@pytest.fixture
def api() -> Any:
    bodies: dict[str, Any] = {"/iss-now.json": fx.ISS, "/planetary/apod": fx.APOD}

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bodies.get(req.url.path, {}))

    client = make_client(handler)
    app.dependency_overrides[get_external_client] = lambda: client
    app.dependency_overrides[get_settings] = lambda: settings()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_route_iss(api: TestClient) -> None:
    body = api.get("/api/v1/iss/position").json()
    assert body["status"] == "ok" and body["source"] == "Open Notify ISS"
    assert set(body) >= {
        "source",
        "status",
        "fetched_at",
        "observed_at",
        "valid_time_start",
        "valid_time_end",
        "stale",
        "units",
        "reference_frame",
        "uncertainty",
        "data",
        "error",
    }


def test_route_validation(api: TestClient) -> None:
    assert api.get("/api/v1/apod", params={"date": "1990-01-01"}).status_code == 422
    assert api.get("/api/v1/ephemerides", params={"target": "301'"}).status_code == 422
    r = api.get("/api/v1/asteroids/feed", params={"start": "2024-05-01", "end": "2024-05-20"})
    assert r.status_code == 422
    assert api.get("/api/v1/events/earth", params={"category": "a;b"}).status_code == 422


def test_route_sources_reports_key_state(api: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: settings(
        app_env="production", nasa_api_key=None
    )
    rows = {r["id"]: r for r in api.get("/api/v1/sources").json()}
    assert rows["apod"]["configured"] is False
    assert rows["eonet"]["configured"] is True
    body = api.get("/api/v1/apod").json()
    assert body["status"] == "not_configured"

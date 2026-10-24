"""Persistência: missões, plano, execução, checkpoints e retomada reprodutível.

Usa TEST_DATABASE_URL (PostgreSQL no CI) ou SQLite temporário localmente.
"""

import math
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_engine, reset_engine_cache
from app.main import app
from app.models import Base

BUS = ["core-s", "obc-1", "sa-600", "bat-1kwh", "ant-lga", "tx-x-20", "rw-set-4", "st-1"]
DESIGN = {
    "stages": [
        {
            "name": "Satélite",
            "parts": [
                *({"component_id": c} for c in BUS),
                {"component_id": "eng-biprop-400"},
                {"component_id": "tank-biprop-150"},
            ],
        }
    ]
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    reset_engine_cache()
    engine = get_engine()
    assert engine is not None
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield TestClient(app)
    Base.metadata.drop_all(engine)
    engine.dispose()
    monkeypatch.delenv("DATABASE_URL")
    get_settings.cache_clear()
    reset_engine_cache()


def new_mission(c: TestClient, **extra: object) -> dict:  # type: ignore[type-arg]
    project = c.post("/api/v1/projects", json={"name": "Agência"}).json()
    body = {
        "project_id": project["id"],
        "name": "Elevação orbital",
        "design": DESIGN,
        "initial_orbit": {"altitude_m": 400e3, "inclination_deg": 51.6},
        "objective": {"target_altitude_m": 2_000e3, "tolerance_m": 1000},
        **extra,
    }
    r = c.post("/api/v1/missions", json=body)
    assert r.status_code == 201, r.text
    m = c.post(f"/api/v1/missions/{r.json()['id']}/plan", json={}).json()
    assert len(m["burns"]) == 2
    return m


def test_without_database_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    reset_engine_cache()
    c = TestClient(app)
    assert c.get("/api/v1/missions").status_code == 503
    assert c.get("/api/v1/health").json()["database"] == "not_configured"


def test_crud_and_listing(client: TestClient) -> None:
    m = new_mission(client)
    assert client.get("/api/v1/health").json()["database"] == "ok"
    assert [x["id"] for x in client.get("/api/v1/missions").json()] == [m["id"]]
    projects = client.get("/api/v1/projects").json()
    assert projects[0]["mission_count"] == 1
    got = client.get(f"/api/v1/missions/{m['id']}").json()
    assert got["physics"]["rtol"] == 1e-11
    assert got["simulator_version"]
    assert client.get("/api/v1/missions/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.delete(f"/api/v1/missions/{m['id']}").status_code == 204
    assert client.get("/api/v1/missions").json() == []


def test_validate_and_run_creates_report(client: TestClient) -> None:
    m = new_mission(client)
    v = client.post(f"/api/v1/missions/{m['id']}/validate").json()
    assert v["valid"] and v["feasibility"]["feasible"]
    run = client.post(f"/api/v1/missions/{m['id']}/run", json={"n_samples": 200}).json()
    sim = run["simulation"]
    assert sim["objective"]["achieved"] is True
    assert client.get(f"/api/v1/missions/{m['id']}").json()["status"] == "simulated"
    reports = client.get(f"/api/v1/missions/{m['id']}/reports").json()
    assert len(reports) == 1
    assert "trajectory" not in reports[0]["summary"]
    assert reports[0]["summary"]["final_mass_kg"] == pytest.approx(sim["final_mass_kg"])


def test_runs_are_deterministic(client: TestClient) -> None:
    m = new_mission(client)
    a = client.post(f"/api/v1/missions/{m['id']}/run", json={"n_samples": 64}).json()
    b = client.post(f"/api/v1/missions/{m['id']}/run", json={"n_samples": 64}).json()
    ta, tb = a["simulation"]["trajectory"], b["simulation"]["trajectory"]
    assert ta["position_m"] == tb["position_m"]
    assert ta["mass_kg"] == tb["mass_kg"]


@pytest.mark.parametrize("where", ["mid_transfer", "at_second_burn"])
def test_checkpoint_resume_reproduces_full_run(client: TestClient, where: str) -> None:
    m = new_mission(client)
    full = client.post(f"/api/v1/missions/{m['id']}/run", json={"n_samples": 64}).json()
    b1, b2 = m["burns"]
    t_ck = (b1["t_s"] + b2["t_s"]) / 2 if where == "mid_transfer" else b2["t_s"]
    ck = client.post(
        f"/api/v1/missions/{m['id']}/checkpoints", json={"t_s": t_ck, "label": "teste"}
    )
    assert ck.status_code == 201, ck.text
    ck_body = ck.json()
    assert ck_body["state"]["source"] == "checkpoint"
    assert ck_body["state"]["mass_kg"] < full["simulation"]["design"]["wet_mass_kg"]
    state = client.get(f"/api/v1/missions/{m['id']}/state").json()
    assert state["t_s"] == pytest.approx(t_ck)

    resumed = client.post(
        f"/api/v1/missions/{m['id']}/checkpoints/{ck_body['id']}/resume", json={"n_samples": 64}
    ).json()
    fs, rs = full["simulation"], resumed["simulation"]
    assert resumed["from_checkpoint_id"] == ck_body["id"]
    # Massa: exata (mesma sequência de Tsiolkovsky; a manobra no instante do checkpoint
    # não é reaplicada). Órbita final: reinício do integrador → tolerância de 1 m.
    assert rs["final_mass_kg"] == pytest.approx(fs["final_mass_kg"], rel=1e-12)
    fo, ro = fs["final_orbit"], rs["final_orbit"]
    assert ro["semi_major_axis_m"] == pytest.approx(fo["semi_major_axis_m"], abs=1.0)
    assert ro["periapsis_altitude_m"] == pytest.approx(fo["periapsis_altitude_m"], abs=1.0)
    assert math.isclose(rs["trajectory"]["t_s"][0], t_ck)
    assert rs["objective"]["achieved"] is True


def test_patch_plan_invalidates_checkpoints(client: TestClient) -> None:
    m = new_mission(client)
    client.post(f"/api/v1/missions/{m['id']}/checkpoints", json={"t_s": 100})
    client.post(f"/api/v1/missions/{m['id']}/run", json={"n_samples": 32})
    renamed = client.patch(f"/api/v1/missions/{m['id']}", json={"name": "Novo nome"}).json()
    assert renamed["checkpoint_count"] == 1 and renamed["status"] == "simulated"
    patched = client.patch(
        f"/api/v1/missions/{m['id']}",
        json={"initial_orbit": {"altitude_m": 500e3, "inclination_deg": 0}},
    ).json()
    assert patched["checkpoint_count"] == 0 and patched["run_count"] == 0
    assert patched["status"] == "draft"


def test_checkpoint_from_other_version_is_refused(client: TestClient) -> None:
    m = new_mission(client)
    ck = client.post(f"/api/v1/missions/{m['id']}/checkpoints", json={"t_s": 50}).json()
    engine = get_engine()
    assert engine is not None
    with engine.begin() as conn:
        conn.exec_driver_sql("UPDATE checkpoints SET simulator_version = '0.0.1'")
    r = client.post(
        f"/api/v1/missions/{m['id']}/checkpoints/{ck['id']}/resume", json={"n_samples": 32}
    )
    assert r.status_code == 409


def test_invalid_inputs(client: TestClient) -> None:
    m = new_mission(client)
    r = client.post(f"/api/v1/missions/{m['id']}/checkpoints", json={"t_s": 1e7})
    assert r.status_code == 422
    project = client.get("/api/v1/projects").json()[0]
    bad = {
        "project_id": project["id"],
        "name": "x",
        "design": {"stages": [{"name": "S", "parts": [{"component_id": "nope"}]}]},
        "initial_orbit": {"altitude_m": 400e3},
    }
    assert client.post("/api/v1/missions", json=bad).status_code == 422
    late = {
        **bad,
        "design": DESIGN,
        "duration_s": 100,
        "burns": [{"t_s": 200, "dv_vnb_ms": [1, 0, 0]}],
    }
    assert client.post("/api/v1/missions", json=late).status_code == 422

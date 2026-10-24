import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BUS = [
    {"component_id": c}
    for c in [
        "core-s",
        "obc-1",
        "sa-600",
        "bat-1kwh",
        "ant-lga",
        "tx-x-20",
        "rw-set-4",
        "st-1",
        "thermal-ctl",
    ]
]
DESIGN = {
    "stages": [
        {
            "name": "Satélite",
            "parts": [
                *BUS,
                {"component_id": "eng-biprop-400"},
                {"component_id": "tank-biprop-150"},
            ],
        }
    ]
}


def test_health() -> None:
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"


def test_catalog() -> None:
    body = client.get("/api/v1/catalog/components").json()
    assert len(body["components"]) >= 10
    assert all(c["fictional"] for c in body["components"])


def test_evaluate() -> None:
    body = client.post("/api/v1/spacecraft/evaluate", json=DESIGN).json()
    assert body["valid"] is True
    assert body["total_delta_v_ms"] > 1000


def test_hohmann_feasibility() -> None:
    req = {"initial_altitude_m": 400e3, "target_altitude_m": 35_786e3, "design": DESIGN}
    body = client.post("/api/v1/planning/hohmann", json=req).json()
    assert body["feasibility"]["feasible"] is False
    assert body["feasibility"]["margin_ms"] < 0
    req["target_altitude_m"] = 1_200e3
    body = client.post("/api/v1/planning/hohmann", json=req).json()
    assert body["feasibility"]["feasible"] is True
    assert len(body["burns"]) == 2


def test_end_to_end_orbit_raise() -> None:
    plan = client.post(
        "/api/v1/planning/hohmann",
        json={"initial_altitude_m": 400e3, "target_altitude_m": 1_200e3, "design": DESIGN},
    ).json()
    req = {
        "design": DESIGN,
        "initial_orbit": {"altitude_m": 400e3, "inclination_deg": 51.6},
        "burns": plan["burns"],
        "duration_s": plan["suggested_duration_s"],
        "objective": {"target_altitude_m": 1_200e3, "tolerance_m": 1000},
    }
    body = client.post("/api/v1/simulations/propagate", json=req).json()
    assert body["objective"]["achieved"] is True
    assert body["final_orbit"]["periapsis_altitude_m"] == pytest.approx(1_200e3, abs=10)
    assert body["propellant_used_kg"] > 0
    assert body["final_mass_kg"] < body["design"]["wet_mass_kg"]
    traj = body["trajectory"]
    assert len(traj["t_s"]) == len(traj["position_m"]) == len(traj["mass_kg"])
    assert body["diagnostics"]["max_rel_energy_drift"] < 1e-8
    assert body["provenance"]["kind"] == "calculated"


def test_validation_errors() -> None:
    r = client.post(
        "/api/v1/planning/hohmann", json={"initial_altitude_m": 10, "target_altitude_m": 1e6}
    )
    assert r.status_code == 422
    bad = {"stages": [{"name": "S", "parts": [{"component_id": "nope"}]}]}
    r = client.post("/api/v1/spacecraft/evaluate", json=bad)
    assert r.status_code == 422
    assert "nope" in r.json()["detail"]


def test_request_size_limit() -> None:
    r = client.post(
        "/api/v1/spacecraft/evaluate",
        content=b"{" + b" " * 300_000 + b"}",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 413

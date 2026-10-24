"""Validação do propagador contra soluções analíticas de Kepler e leis de conservação.

Tolerâncias documentadas em docs/validation.md.
"""

import math

import numpy as np
import pytest

from app.domain.constants import G0, MU_EARTH, R_EARTH_EQ
from app.domain.orbital_mechanics.elements import OrbitalElements, elements_to_state, orbital_period
from app.services.flight import circular_orbit_state, plan_hohmann, summarize_earth
from app.simulation.propagator import Burn, IntegratorSettings, StageTank, propagate

MU = MU_EARTH


def kepler_state(el: OrbitalElements, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Solução analítica (órbita elíptica) por Newton-Raphson na equação de Kepler."""
    a, e = el.semi_major_axis, el.eccentricity
    nu0 = el.true_anomaly
    e_anom0 = 2 * math.atan(math.sqrt((1 - e) / (1 + e)) * math.tan(nu0 / 2))
    m = e_anom0 - e * math.sin(e_anom0) + math.sqrt(MU / a**3) * dt
    big_e = m
    for _ in range(50):
        big_e -= (big_e - e * math.sin(big_e) - m) / (1 - e * math.cos(big_e))
    nu = 2 * math.atan2(
        math.sqrt(1 + e) * math.sin(big_e / 2), math.sqrt(1 - e) * math.cos(big_e / 2)
    )
    return elements_to_state(
        OrbitalElements(a, e, el.inclination, el.raan, el.arg_periapsis, nu), MU
    )


def inert(mass: float = 1000.0) -> list[StageTank]:
    return [StageTank("S", 0.0, None, 0.0, mass)]


ELLIPSE = OrbitalElements(R_EARTH_EQ + 12_000e3, 0.6, 0.5, 0.3, 1.1, 0.2)


def test_matches_kepler_over_ten_periods() -> None:
    r0, v0 = elements_to_state(ELLIPSE, MU)
    period = orbital_period(ELLIPSE.semi_major_axis, MU)
    res = propagate(r0, v0, inert(), [], 10 * period, MU, R_EARTH_EQ, n_samples=200)
    r_ref, v_ref = kepler_state(ELLIPSE, 10 * period)
    # Tolerância: 1 m em posição após 10 órbitas (~ 2,9 dias) com rtol = 1e-11 (padrão).
    assert np.linalg.norm(res.r[-1] - r_ref) < 1.0
    assert np.linalg.norm(res.v[-1] - v_ref) < 1e-3


def test_energy_and_angular_momentum_conserved() -> None:
    r0, v0 = elements_to_state(ELLIPSE, MU)
    period = orbital_period(ELLIPSE.semi_major_axis, MU)
    res = propagate(r0, v0, inert(), [], 10 * period, MU, R_EARTH_EQ, n_samples=1000)
    # Tolerância relativa: 1e-9 (cenário conservativo, rtol = 1e-11).
    assert res.max_rel_energy_drift < 1e-9
    assert res.max_rel_h_drift < 1e-9


def test_convergence_with_tolerance() -> None:
    r0, v0 = elements_to_state(ELLIPSE, MU)
    t = 5 * orbital_period(ELLIPSE.semi_major_axis, MU)
    r_ref, _ = kepler_state(ELLIPSE, t)
    errors = []
    for rtol in (1e-7, 1e-9, 1e-11):
        s = IntegratorSettings(rtol=rtol, atol_position_m=1e-6, atol_velocity_ms=1e-9)
        res = propagate(r0, v0, inert(), [], t, MU, R_EARTH_EQ, n_samples=16, settings=s)
        errors.append(float(np.linalg.norm(res.r[-1] - r_ref)))
    assert errors[0] > errors[1] > errors[2]
    assert errors[2] < 0.5


def test_hohmann_reaches_target_and_accounts_propellant() -> None:
    r0, v0 = circular_orbit_state(400e3, math.radians(28.5))
    plan = plan_hohmann(400e3, 2_000e3, 300.0)
    stack = [StageTank("S", 200.0, 318.0, 400.0, 600.0)]
    res = propagate(r0, v0, stack, list(plan.burns), plan.suggested_duration_s, MU, R_EARTH_EQ)
    final = summarize_earth(res.r[-1], res.v[-1])
    target = R_EARTH_EQ + 2_000e3
    # Queimas impulsivas exatas: erro de raio < 10 m e excentricidade < 1e-6.
    assert final.periapsis_radius == pytest.approx(target, abs=10.0)
    assert final.apoapsis_radius == pytest.approx(target, abs=10.0)
    assert final.elements.eccentricity < 1e-6
    assert final.elements.inclination == pytest.approx(math.radians(28.5), abs=1e-9)
    dv = plan.transfer.total_dv
    assert res.dv_executed_ms == pytest.approx(dv, rel=1e-12)
    expected_used = 800.0 * (1 - math.exp(-dv / (318.0 * G0)))
    assert res.propellant_used_kg == pytest.approx(expected_used, rel=1e-12)
    assert res.mass[-1] == pytest.approx(800.0 - expected_used, rel=1e-12)
    assert [e.kind for e in res.events].count("burn") == 2


def test_insufficient_propellant_partial_burn() -> None:
    r0, v0 = circular_orbit_state(400e3, 0.0)
    stack = [StageTank("S", 5.0, 230.0, 22.0, 500.0)]
    res = propagate(r0, v0, stack, [Burn(10.0, (500.0, 0, 0))], 4000.0, MU, R_EARTH_EQ)
    kinds = [e.kind for e in res.events]
    assert "propellant_depleted" in kinds
    available = 230.0 * G0 * math.log(505.0 / 500.0)
    assert res.dv_executed_ms == pytest.approx(available, rel=1e-12)
    assert res.mass[-1] == pytest.approx(500.0)


def test_staging_jettisons_lower_stage() -> None:
    r0, v0 = circular_orbit_state(400e3, 0.0)
    stack = [
        StageTank("Inferior", 50.0, 318.0, 400.0, 30.0),
        StageTank("Satélite", 40.0, 230.0, 88.0, 150.0),
    ]
    m0 = 270.0
    dv_lower = 318.0 * G0 * math.log(m0 / (m0 - 50.0))
    res = propagate(r0, v0, stack, [Burn(10.0, (dv_lower + 50.0, 0, 0))], 1000.0, MU, R_EARTH_EQ)
    kinds = [e.kind for e in res.events]
    assert "stage_separation" in kinds
    used_upper = 190.0 * (1 - math.exp(-50.0 / (230.0 * G0)))
    assert res.mass[-1] == pytest.approx(190.0 - used_upper, rel=1e-12)


def test_deorbit_burn_impacts_and_stops() -> None:
    r0, v0 = circular_orbit_state(300e3, 0.0)
    stack = [StageTank("S", 500.0, 318.0, 400.0, 300.0)]
    res = propagate(r0, v0, stack, [Burn(0.0, (-1500.0, 0, 0))], 20_000.0, MU, R_EARTH_EQ)
    assert res.terminated_early
    assert res.events[-1].kind == "impact"
    assert np.linalg.norm(res.r[-1]) == pytest.approx(R_EARTH_EQ, abs=1.0)


def test_burn_frame_normal_changes_inclination_only() -> None:
    r0, v0 = circular_orbit_state(500e3, 0.0)
    v = float(np.linalg.norm(v0))
    di = math.radians(1.0)
    dv_n = 2 * v * math.sin(di / 2)
    # Mudança de plano pura: componente V negativa + N, mantendo |v|.
    burn = Burn(0.0, (v * math.cos(di) - v, v * math.sin(di), 0.0))
    res = propagate(
        r0, v0, [StageTank("S", 1e4, 300, 1e3, 1e3)], [burn], 100.0, MU, R_EARTH_EQ, n_samples=16
    )
    final = summarize_earth(res.r[-1], res.v[-1])
    assert final.elements.inclination == pytest.approx(di, abs=1e-12)
    assert final.elements.eccentricity < 1e-9
    assert res.dv_executed_ms == pytest.approx(dv_n, rel=1e-9)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"duration_s": -1.0},
        {"duration_s": 1e9},
        {"n_samples": 10},
        {"burns": [Burn(1e6, (1, 0, 0))]},
        {"burns": [Burn(1.0, (math.nan, 0, 0))]},
    ],
)
def test_rejects_unbounded_or_invalid_inputs(kwargs: dict[str, object]) -> None:
    r0, v0 = circular_orbit_state(400e3, 0.0)
    args: dict[str, object] = {"duration_s": 1000.0, "burns": []}
    args.update(kwargs)
    with pytest.raises(ValueError):
        propagate(r0, v0, inert(), mu=MU, body_radius_m=R_EARTH_EQ, **args)  # type: ignore[arg-type]

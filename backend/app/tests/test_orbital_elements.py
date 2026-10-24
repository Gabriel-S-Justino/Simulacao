"""Conversões e invariantes analíticos. Tolerâncias: relativas 1e-12 salvo indicação."""

import math

import numpy as np
import pytest

from app.domain.constants import MU_EARTH, R_EARTH_EQ
from app.domain.orbital_mechanics.elements import (
    OrbitalElements,
    circular_speed,
    elements_to_state,
    escape_speed,
    orbital_period,
    state_to_elements,
    summarize,
)

MU = MU_EARTH


@pytest.mark.parametrize(
    "el",
    [
        OrbitalElements(7_000_000.0, 0.01, 0.9, 1.2, 0.4, 2.0),
        OrbitalElements(26_600_000.0, 0.74, math.radians(63.4), 4.0, math.radians(270), 0.3),
        OrbitalElements(-20_000_000.0, 1.5, 0.3, 0.2, 1.0, 0.5),  # hiperbólica
        OrbitalElements(42_164_000.0, 0.2, math.radians(150), 3.0, 5.0, 4.0),  # retrógrada
    ],
)
def test_elements_round_trip(el: OrbitalElements) -> None:
    r, v = elements_to_state(el, MU)
    back = state_to_elements(r, v, MU)
    assert back.semi_major_axis == pytest.approx(el.semi_major_axis, rel=1e-11)
    assert back.eccentricity == pytest.approx(el.eccentricity, rel=1e-10)
    assert back.inclination == pytest.approx(el.inclination, abs=1e-12)
    assert back.raan == pytest.approx(el.raan, abs=1e-10)
    assert back.arg_periapsis == pytest.approx(el.arg_periapsis, abs=1e-9)
    assert back.true_anomaly == pytest.approx(el.true_anomaly, abs=1e-9)


def test_circular_equatorial_round_trip() -> None:
    el = OrbitalElements(R_EARTH_EQ + 400e3, 0.0, 0.0, 0.0, 0.0, 1.3)
    r, v = elements_to_state(el, MU)
    s = summarize(r, v, MU)
    assert s.orbit_type == "circular"
    assert s.elements.true_anomaly == pytest.approx(1.3, abs=1e-12)
    assert np.linalg.norm(v) == pytest.approx(circular_speed(R_EARTH_EQ + 400e3, MU), rel=1e-14)


def test_known_values_leo_iss_like() -> None:
    # Órbita circular a 400 km: v ≈ 7,669 km/s, T ≈ 92,56 min (valores analíticos de referência).
    r = R_EARTH_EQ + 400e3
    assert circular_speed(r, MU) == pytest.approx(7668.6, abs=0.1)
    assert orbital_period(r, MU) / 60 == pytest.approx(92.56, abs=0.01)


def test_geo_period_is_sidereal_day() -> None:
    # Raio geoestacionário 42 164,17 km → período = dia sideral (86 164,09 s) a ±1 s.
    assert orbital_period(42_164_170.0, MU) == pytest.approx(86_164.09, abs=1.0)


def test_escape_speed_surface() -> None:
    # Velocidade de escape no raio equatorial (6378,137 km) ≈ 11,180 km/s
    # (11,186 km/s é o valor para o raio médio de 6371 km).
    assert escape_speed(R_EARTH_EQ, MU) == pytest.approx(11_180.0, abs=1.0)
    assert escape_speed(6_371_000.0, MU) == pytest.approx(11_186.0, abs=1.0)
    assert escape_speed(7e6, MU) == pytest.approx(math.sqrt(2) * circular_speed(7e6, MU), rel=1e-15)


def test_energy_sign_by_orbit_type() -> None:
    r = np.array([7e6, 0, 0])
    vesc = escape_speed(7e6, MU)
    assert summarize(r, np.array([0, 0.9 * vesc, 0]), MU).specific_energy < 0
    hyp = summarize(r, np.array([0, 1.1 * vesc, 0]), MU)
    assert hyp.specific_energy > 0
    assert hyp.orbit_type == "hyperbolic"
    assert hyp.period is None and hyp.apoapsis_radius is None


def test_rejects_radial_trajectory() -> None:
    with pytest.raises(ValueError):
        state_to_elements(np.array([7e6, 0, 0]), np.array([1000.0, 0, 0]), MU)

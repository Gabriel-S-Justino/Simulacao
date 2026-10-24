"""Conversões entre estado cartesiano e elementos orbitais clássicos (dois corpos).

Todas as grandezas em SI (m, m/s, rad). O referencial é o do vetor de estado
recebido (no simulador: ECI inercial centrado na Terra, eixos tipo J2000).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Vec = NDArray[np.float64]

_EPS = 1e-11


@dataclass(frozen=True, slots=True)
class OrbitalElements:
    """Elementos clássicos. Para órbitas hiperbólicas, a < 0 e o período é None."""

    semi_major_axis: float  # m (negativo se hiperbólica)
    eccentricity: float
    inclination: float  # rad
    raan: float  # rad
    arg_periapsis: float  # rad
    true_anomaly: float  # rad


@dataclass(frozen=True, slots=True)
class OrbitSummary:
    elements: OrbitalElements
    specific_energy: float  # J/kg
    specific_angular_momentum: float  # m^2/s
    periapsis_radius: float  # m
    apoapsis_radius: float | None  # m, None se a órbita não é fechada
    period: float | None  # s, None se a órbita não é fechada
    orbit_type: str  # "circular" | "elliptic" | "parabolic" | "hyperbolic"


def specific_energy(r: Vec, v: Vec, mu: float) -> float:
    return float(np.dot(v, v) / 2.0 - mu / np.linalg.norm(r))


def angular_momentum(r: Vec, v: Vec) -> Vec:
    return np.cross(r, v)


def circular_speed(radius: float, mu: float) -> float:
    return math.sqrt(mu / radius)


def escape_speed(radius: float, mu: float) -> float:
    return math.sqrt(2.0 * mu / radius)


def vis_viva_speed(radius: float, semi_major_axis: float, mu: float) -> float:
    return math.sqrt(mu * (2.0 / radius - 1.0 / semi_major_axis))


def orbital_period(semi_major_axis: float, mu: float) -> float:
    if semi_major_axis <= 0:
        raise ValueError("Período definido apenas para órbitas fechadas (a > 0).")
    return 2.0 * math.pi * math.sqrt(semi_major_axis**3 / mu)


def state_to_elements(r: Vec, v: Vec, mu: float) -> OrbitalElements:
    r = np.asarray(r, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    rn = float(np.linalg.norm(r))
    vn = float(np.linalg.norm(v))
    if rn <= 0 or not math.isfinite(rn) or not math.isfinite(vn):
        raise ValueError("Estado inválido.")

    h = np.cross(r, v)
    hn = float(np.linalg.norm(h))
    if hn < _EPS * rn * max(vn, 1.0):
        raise ValueError("Trajetória retilínea (h = 0) não possui elementos clássicos.")
    k = np.array([0.0, 0.0, 1.0])
    n = np.cross(k, h)
    nn = float(np.linalg.norm(n))
    e_vec = ((vn**2 - mu / rn) * r - float(np.dot(r, v)) * v) / mu
    e = float(np.linalg.norm(e_vec))
    energy = vn**2 / 2.0 - mu / rn
    a = math.inf if abs(energy) < 1e-12 * mu / rn else -mu / (2.0 * energy)

    i = math.acos(_clip(h[2] / hn))

    equatorial = nn < _EPS * hn
    circular = e < 1e-10

    if equatorial:
        raan = 0.0
    else:
        raan = math.acos(_clip(n[0] / nn))
        if n[1] < 0:
            raan = 2.0 * math.pi - raan

    if circular:
        argp = 0.0
        if equatorial:
            # longitude verdadeira
            nu = math.acos(_clip(r[0] / rn))
            if r[1] < 0:
                nu = 2.0 * math.pi - nu
            if h[2] < 0:
                nu = 2.0 * math.pi - nu
        else:
            # argumento de latitude
            nu = math.acos(_clip(float(np.dot(n, r)) / (nn * rn)))
            if r[2] < 0:
                nu = 2.0 * math.pi - nu
    else:
        if equatorial:
            # longitude do periapsis
            argp = math.atan2(e_vec[1], e_vec[0])
            if h[2] < 0:
                argp = -argp
            argp %= 2.0 * math.pi
        else:
            argp = math.acos(_clip(float(np.dot(n, e_vec)) / (nn * e)))
            if e_vec[2] < 0:
                argp = 2.0 * math.pi - argp
        nu = math.acos(_clip(float(np.dot(e_vec, r)) / (e * rn)))
        if float(np.dot(r, v)) < 0:
            nu = 2.0 * math.pi - nu

    return OrbitalElements(a, e, i, raan, argp, nu)


def elements_to_state(el: OrbitalElements, mu: float) -> tuple[Vec, Vec]:
    a, e = el.semi_major_axis, el.eccentricity
    if abs(e - 1.0) < 1e-12:
        raise ValueError("Órbita parabólica: use o parâmetro semilatus rectum diretamente.")
    p = a * (1.0 - e * e)
    if p <= 0:
        raise ValueError("Combinação inválida de a e e.")
    nu = el.true_anomaly
    if e > 1.0 and 1.0 + e * math.cos(nu) <= 0:
        raise ValueError("Anomalia verdadeira fora do ramo hiperbólico.")
    r_pf = (p / (1.0 + e * math.cos(nu))) * np.array([math.cos(nu), math.sin(nu), 0.0])
    v_pf = math.sqrt(mu / p) * np.array([-math.sin(nu), e + math.cos(nu), 0.0])
    rot = _perifocal_to_inertial(el.raan, el.inclination, el.arg_periapsis)
    return rot @ r_pf, rot @ v_pf


def summarize(r: Vec, v: Vec, mu: float) -> OrbitSummary:
    el = state_to_elements(r, v, mu)
    eps = specific_energy(r, v, mu)
    h = float(np.linalg.norm(angular_momentum(r, v)))
    e = el.eccentricity
    p = h * h / mu
    rp = p / (1.0 + e)
    if e < 1.0:
        a = el.semi_major_axis
        ra: float | None = p / (1.0 - e)
        period: float | None = orbital_period(a, mu)
        kind = "circular" if e < 1e-6 else "elliptic"
    else:
        ra = None
        period = None
        kind = "parabolic" if abs(e - 1.0) < 1e-9 else "hyperbolic"
    return OrbitSummary(el, eps, h, rp, ra, period, kind)


def _perifocal_to_inertial(raan: float, inc: float, argp: float) -> Vec:
    co, so = math.cos(raan), math.sin(raan)
    ci, si = math.cos(inc), math.sin(inc)
    cw, sw = math.cos(argp), math.sin(argp)
    return np.array(
        [
            [co * cw - so * sw * ci, -co * sw - so * cw * ci, so * si],
            [so * cw + co * sw * ci, -so * sw + co * cw * ci, -co * si],
            [sw * si, cw * si, ci],
        ]
    )


def _clip(x: float) -> float:
    return max(-1.0, min(1.0, float(x)))

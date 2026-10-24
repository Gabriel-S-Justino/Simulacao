"""Orquestra a fatia vertical: projeto → plano → propagação → avaliação do objetivo."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.domain.constants import MU_EARTH, R_EARTH_EQ
from app.domain.orbital_mechanics.elements import (
    OrbitalElements,
    OrbitSummary,
    elements_to_state,
    summarize,
)
from app.domain.orbital_mechanics.maneuvers import HohmannTransfer, hohmann
from app.domain.spacecraft.design import DesignReport
from app.simulation.propagator import Burn, StageTank

MIN_ALTITUDE_M = 150_000.0
MAX_ALTITUDE_M = 400_000_000.0  # ~ além da órbita lunar; fora disso a hipótese de 2 corpos falha


def circular_orbit_state(
    altitude_m: float, inclination_rad: float
) -> tuple[np.ndarray, np.ndarray]:
    _check_altitude(altitude_m)
    el = OrbitalElements(R_EARTH_EQ + altitude_m, 0.0, inclination_rad, 0.0, 0.0, 0.0)
    return elements_to_state(el, MU_EARTH)


def build_stack(report: DesignReport) -> list[StageTank]:
    stack: list[StageTank] = []
    n = len(report.stages)
    for i, st in enumerate(report.stages):
        upper = report.stages[i + 1].initial_mass_kg if i + 1 < n else 0.0
        jettison = st.initial_mass_kg - st.propellant_kg - upper
        stack.append(StageTank(st.name, st.propellant_kg, st.isp_s, st.thrust_n, jettison))
    return stack


@dataclass(frozen=True, slots=True)
class HohmannPlan:
    transfer: HohmannTransfer
    burns: tuple[Burn, ...]
    suggested_duration_s: float


def plan_hohmann(
    initial_altitude_m: float, target_altitude_m: float, t_start_s: float
) -> HohmannPlan:
    _check_altitude(initial_altitude_m)
    _check_altitude(target_altitude_m)
    r1 = R_EARTH_EQ + initial_altitude_m
    r2 = R_EARTH_EQ + target_altitude_m
    tr = hohmann(r1, r2, MU_EARTH)
    burns = (
        Burn(t_start_s, (tr.dv1, 0.0, 0.0), "Injeção na transferência"),
        Burn(t_start_s + tr.transfer_time, (tr.dv2, 0.0, 0.0), "Circularização"),
    )
    final_period = 2 * math.pi * math.sqrt(r2**3 / MU_EARTH)
    duration = t_start_s + tr.transfer_time + final_period
    return HohmannPlan(tr, burns, duration)


@dataclass(frozen=True, slots=True)
class ObjectiveResult:
    achieved: bool
    periapsis_error_m: float
    apoapsis_error_m: float | None
    tolerance_m: float


def evaluate_circular_target(
    final: OrbitSummary, target_altitude_m: float, tolerance_m: float, impacted: bool
) -> ObjectiveResult:
    target_r = R_EARTH_EQ + target_altitude_m
    pe = final.periapsis_radius - target_r
    ae = None if final.apoapsis_radius is None else final.apoapsis_radius - target_r
    ok = not impacted and abs(pe) <= tolerance_m and ae is not None and abs(ae) <= tolerance_m
    return ObjectiveResult(ok, pe, ae, tolerance_m)


def summarize_earth(r: np.ndarray, v: np.ndarray) -> OrbitSummary:
    return summarize(r, v, MU_EARTH)


def _check_altitude(alt: float) -> None:
    if not MIN_ALTITUDE_M <= alt <= MAX_ALTITUDE_M:
        raise ValueError(
            f"Altitude deve estar entre {MIN_ALTITUDE_M / 1000:.0f} km e "
            f"{MAX_ALTITUDE_M / 1000:.0f} km."
        )

"""Equação de Tsiolkovsky e consumo de propelente."""

from __future__ import annotations

import math
from collections.abc import Sequence

from app.domain.constants import G0


def delta_v(isp: float, m0: float, mf: float) -> float:
    """Delta-v ideal (m/s): Isp * g0 * ln(m0/mf)."""
    if isp <= 0 or m0 <= 0 or mf <= 0 or mf > m0:
        raise ValueError("Parâmetros inválidos para Tsiolkovsky.")
    return isp * G0 * math.log(m0 / mf)


def propellant_for_dv(isp: float, m0: float, dv: float) -> float:
    """Massa de propelente (kg) consumida para produzir dv a partir de m0."""
    if isp <= 0 or m0 <= 0 or dv < 0:
        raise ValueError("Parâmetros inválidos.")
    return m0 * (1.0 - math.exp(-dv / (isp * G0)))


def combined_isp(engines: Sequence[tuple[float, float]]) -> float:
    """Isp efetivo de motores acionados simultaneamente: ΣF / Σ(F/Isp).

    `engines` é uma sequência de pares (empuxo N, Isp s).
    """
    total_f = sum(f for f, _ in engines)
    total_mdot = sum(f / isp for f, isp in engines)
    if total_f <= 0 or total_mdot <= 0:
        raise ValueError("Sem motores válidos.")
    return total_f / total_mdot


def burn_duration(thrust: float, isp: float, propellant_mass: float) -> float:
    """Duração (s) de queima a empuxo constante: m_p / ṁ, com ṁ = F/(Isp g0)."""
    mdot = thrust / (isp * G0)
    return propellant_mass / mdot

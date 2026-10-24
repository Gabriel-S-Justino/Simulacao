"""Planejamento de manobras impulsivas coplanares.

Hipóteses (aproximação explícita): dois corpos, órbitas circulares coplanares,
queimas instantâneas (impulsivas). O tempo finito de queima é reportado à parte.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.orbital_mechanics.elements import circular_speed


@dataclass(frozen=True, slots=True)
class HohmannTransfer:
    r1: float
    r2: float
    dv1: float  # m/s, com sinal: positivo = prograde
    dv2: float  # m/s, com sinal
    transfer_time: float  # s (meia elipse)
    transfer_semi_major_axis: float

    @property
    def total_dv(self) -> float:
        return abs(self.dv1) + abs(self.dv2)


def hohmann(r1: float, r2: float, mu: float) -> HohmannTransfer:
    if r1 <= 0 or r2 <= 0:
        raise ValueError("Raios devem ser positivos.")
    a_t = (r1 + r2) / 2.0
    v1 = circular_speed(r1, mu)
    v2 = circular_speed(r2, mu)
    v_tp = math.sqrt(mu * (2.0 / r1 - 1.0 / a_t))  # na partida
    v_ta = math.sqrt(mu * (2.0 / r2 - 1.0 / a_t))  # na chegada
    tof = math.pi * math.sqrt(a_t**3 / mu)
    return HohmannTransfer(r1, r2, v_tp - v1, v2 - v_ta, tof, a_t)


def bi_elliptic(r1: float, r2: float, rb: float, mu: float) -> tuple[float, float, float, float]:
    """Transferência bi-elíptica. Retorna (dv1, dv2, dv3, tempo total)."""
    if rb < max(r1, r2):
        raise ValueError("O raio intermediário deve ser maior que r1 e r2.")
    a1 = (r1 + rb) / 2.0
    a2 = (r2 + rb) / 2.0
    dv1 = math.sqrt(mu * (2 / r1 - 1 / a1)) - math.sqrt(mu / r1)
    dv2 = math.sqrt(mu * (2 / rb - 1 / a2)) - math.sqrt(mu * (2 / rb - 1 / a1))
    dv3 = math.sqrt(mu * (2 / r2 - 1 / a2)) - math.sqrt(mu / r2)
    t = math.pi * (math.sqrt(a1**3 / mu) + math.sqrt(a2**3 / mu))
    return dv1, dv2, dv3, t

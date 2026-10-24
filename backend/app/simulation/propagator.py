"""Propagador de dois corpos com manobras impulsivas e consumo de propelente.

Modelo: gravidade central newtoniana (sem perturbações), integrador DOP853
(Runge-Kutta 8(5,3) com controle de erro, Hairer & Wanner) via SciPy.
Manobras: impulsivas, aplicadas no referencial local VNB
(V = velocidade, N = normal ao plano orbital, B = V x N).
O tempo da simulação é independente de qualquer taxa de quadros.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from app.domain.constants import G0
from app.domain.orbital_mechanics.elements import orbital_period, summarize

Vec = NDArray[np.float64]

MAX_DURATION_S = 30.0 * 86400.0
MAX_BURNS = 32
MAX_SAMPLES = 6000
MIN_SAMPLES = 16


@dataclass(frozen=True, slots=True)
class IntegratorSettings:
    rtol: float = 1e-11
    atol_position_m: float = 1e-6
    atol_velocity_ms: float = 1e-9
    max_step_s: float = math.inf

    def validate(self) -> None:
        if not 1e-13 <= self.rtol <= 1e-6:
            raise ValueError("rtol fora do intervalo permitido [1e-13, 1e-6].")
        if self.atol_position_m <= 0 or self.atol_velocity_ms <= 0:
            raise ValueError("Tolerâncias absolutas devem ser positivas.")


@dataclass(slots=True)
class StageTank:
    """Propulsão disponível num estágio durante o voo."""

    name: str
    burnable_kg: float
    isp_s: float | None
    thrust_n: float
    jettison_mass_kg: float  # massa descartada na separação (sem o propelente queimável)


@dataclass(frozen=True, slots=True)
class Burn:
    t: float  # s desde o início
    dv_vnb: tuple[float, float, float]  # m/s
    label: str = ""


EventKind = Literal[
    "burn", "stage_separation", "propellant_depleted", "impact", "finite_burn_warning"
]


@dataclass(frozen=True, slots=True)
class SimEvent:
    t: float
    kind: EventKind
    message: str
    data: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SimResult:
    t: Vec  # (n,)
    r: Vec  # (n,3) m
    v: Vec  # (n,3) m/s
    mass: Vec  # (n,) kg
    events: tuple[SimEvent, ...]
    dv_executed_ms: float
    propellant_used_kg: float
    max_rel_energy_drift: float  # deriva máxima entre manobras (deve ser ~0)
    max_rel_h_drift: float
    terminated_early: bool
    nfev: int


def propagate(
    r0: Vec,
    v0: Vec,
    stages: list[StageTank],
    burns: list[Burn],
    duration_s: float,
    mu: float,
    body_radius_m: float,
    n_samples: int = 1500,
    settings: IntegratorSettings | None = None,
) -> SimResult:
    settings = settings or IntegratorSettings()
    settings.validate()
    if not 0 < duration_s <= MAX_DURATION_S:
        raise ValueError(f"Duração deve estar em (0, {MAX_DURATION_S:.0f}] s.")
    if len(burns) > MAX_BURNS:
        raise ValueError(f"No máximo {MAX_BURNS} manobras.")
    if not MIN_SAMPLES <= n_samples <= MAX_SAMPLES:
        raise ValueError(f"Amostras devem estar em [{MIN_SAMPLES}, {MAX_SAMPLES}].")
    for b in burns:
        if not 0 <= b.t <= duration_s:
            raise ValueError("Manobra fora do intervalo de simulação.")
        if not all(math.isfinite(x) for x in b.dv_vnb):
            raise ValueError("Delta-v de manobra inválido.")

    r = np.asarray(r0, dtype=np.float64).copy()
    v = np.asarray(v0, dtype=np.float64).copy()
    if np.linalg.norm(r) <= body_radius_m:
        raise ValueError("Estado inicial abaixo da superfície.")

    stack = [
        StageTank(s.name, s.burnable_kg, s.isp_s, s.thrust_n, s.jettison_mass_kg) for s in stages
    ]
    mass = sum(s.burnable_kg + s.jettison_mass_kg for s in stack)
    stage_idx = 0

    ordered = sorted(burns, key=lambda b: b.t)
    boundaries = [0.0] + [b.t for b in ordered] + [duration_s]
    grid = np.linspace(0.0, duration_s, n_samples)

    atol = np.array([settings.atol_position_m] * 3 + [settings.atol_velocity_ms] * 3)

    def rhs(_t: float, y: Vec) -> Vec:
        rr = y[:3]
        rn = math.sqrt(rr[0] * rr[0] + rr[1] * rr[1] + rr[2] * rr[2])
        acc = -mu * rr / (rn * rn * rn)
        return np.concatenate((y[3:], acc))

    def impact(_t: float, y: Vec) -> float:
        return float(np.linalg.norm(y[:3]) - body_radius_m)

    impact.terminal = True  # type: ignore[attr-defined]
    impact.direction = -1  # type: ignore[attr-defined]

    ts: list[float] = []
    rs: list[Vec] = []
    vs: list[Vec] = []
    ms: list[float] = []
    events: list[SimEvent] = []
    dv_exec_total = 0.0
    prop_total = 0.0
    max_e_drift = 0.0
    max_h_drift = 0.0
    nfev = 0
    terminated = False

    for seg in range(len(boundaries) - 1):
        t_a, t_b = boundaries[seg], boundaries[seg + 1]
        if seg > 0:
            burn = ordered[seg - 1]
            v, mass, stage_idx, dv_done, used, evs = _apply_burn(
                r, v, mass, stack, stage_idx, burn, mu
            )
            dv_exec_total += dv_done
            prop_total += used
            events.extend(evs)
        if t_b <= t_a:
            if seg == len(boundaries) - 2:
                ts.append(t_a)
                rs.append(r.copy())
                vs.append(v.copy())
                ms.append(mass)
            continue
        sol = solve_ivp(
            rhs,
            (t_a, t_b),
            np.concatenate((r, v)),
            method="DOP853",
            rtol=settings.rtol,
            atol=atol,
            max_step=settings.max_step_s,
            dense_output=True,
            events=impact,
        )
        nfev += int(sol.nfev)
        if sol.status < 0:
            raise RuntimeError(f"Falha numérica do integrador: {sol.message}")
        t_end = float(sol.t[-1])
        inner = grid[(grid >= t_a) & (grid <= t_end)]
        pts = np.unique(np.concatenate(([t_a], inner, [t_end])))
        ys = sol.sol(pts)
        e0 = _energy(ys[:3, 0], ys[3:, 0], mu)
        h0 = float(np.linalg.norm(np.cross(ys[:3, 0], ys[3:, 0])))
        for k, tk in enumerate(pts):
            rk, vk = ys[:3, k], ys[3:, k]
            ts.append(float(tk))
            rs.append(rk.copy())
            vs.append(vk.copy())
            ms.append(mass)
            max_e_drift = max(max_e_drift, abs(_energy(rk, vk, mu) - e0) / abs(e0))
            hk = float(np.linalg.norm(np.cross(rk, vk)))
            max_h_drift = max(max_h_drift, abs(hk - h0) / h0)
        r = ys[:3, -1].copy()
        v = ys[3:, -1].copy()
        if sol.status == 1:
            terminated = True
            events.append(SimEvent(t_end, "impact", "Impacto com a superfície."))
            break

    return SimResult(
        t=np.asarray(ts),
        r=np.asarray(rs),
        v=np.asarray(vs),
        mass=np.asarray(ms),
        events=tuple(sorted(events, key=lambda e: e.t)),
        dv_executed_ms=dv_exec_total,
        propellant_used_kg=prop_total,
        max_rel_energy_drift=max_e_drift,
        max_rel_h_drift=max_h_drift,
        terminated_early=terminated,
        nfev=nfev,
    )


def _energy(r: Vec, v: Vec, mu: float) -> float:
    return float(np.dot(v, v) / 2.0 - mu / np.linalg.norm(r))


def vnb_basis(r: Vec, v: Vec) -> tuple[Vec, Vec, Vec]:
    vh = v / np.linalg.norm(v)
    h = np.cross(r, v)
    nh = h / np.linalg.norm(h)
    bh = np.cross(vh, nh)
    return vh, nh, bh


def _apply_burn(
    r: Vec,
    v: Vec,
    mass: float,
    stack: list[StageTank],
    stage_idx: int,
    burn: Burn,
    mu: float,
) -> tuple[Vec, float, int, float, float, list[SimEvent]]:
    events: list[SimEvent] = []
    vh, nh, bh = vnb_basis(r, v)
    dv_vec = burn.dv_vnb[0] * vh + burn.dv_vnb[1] * nh + burn.dv_vnb[2] * bh
    requested = float(np.linalg.norm(dv_vec))
    if requested == 0.0:
        return v, mass, stage_idx, 0.0, 0.0, events
    direction = dv_vec / requested

    done = 0.0
    used_total = 0.0
    burn_time = 0.0
    while requested - done > 1e-9:
        stage = stack[stage_idx]
        last = stage_idx == len(stack) - 1
        if stage.burnable_kg <= 1e-9 or stage.isp_s is None or stage.thrust_n <= 0:
            if last:
                break
            mass -= stage.jettison_mass_kg + stage.burnable_kg
            events.append(_separation(burn.t, stage))
            stage_idx += 1
            continue
        ve = stage.isp_s * G0
        avail = ve * math.log(mass / (mass - stage.burnable_kg))
        take = min(avail, requested - done)
        used = mass * (1.0 - math.exp(-take / ve))
        used = min(used, stage.burnable_kg)
        stage.burnable_kg -= used
        mass -= used
        used_total += used
        done += take
        burn_time += used / (stage.thrust_n / ve)
        if stage.burnable_kg <= 1e-9 and not last:
            mass -= stage.jettison_mass_kg
            events.append(_separation(burn.t, stage))
            stage_idx += 1

    v_new = v + direction * done
    label = burn.label or "Manobra"
    events.append(
        SimEvent(
            burn.t,
            "burn",
            f"{label}: {done:.1f} m/s executados.",
            {
                "requested_ms": requested,
                "executed_ms": done,
                "propellant_kg": used_total,
                "finite_burn_s": burn_time,
            },
        )
    )
    if requested - done > 1e-6:
        events.append(
            SimEvent(
                burn.t,
                "propellant_depleted",
                f"Propelente esgotado: faltaram {requested - done:.1f} m/s.",
                {"missing_ms": requested - done},
            )
        )
    s = summarize(r, v, mu)
    period = orbital_period(s.elements.semi_major_axis, mu) if s.period else None
    if period and burn_time > 0.05 * period:
        events.append(
            SimEvent(
                burn.t,
                "finite_burn_warning",
                "Queima longa: a aproximação impulsiva perde precisão.",
                {"burn_time_s": burn_time, "period_s": period},
            )
        )
    return v_new, mass, stage_idx, done, used_total, events


def _separation(t: float, stage: StageTank) -> SimEvent:
    return SimEvent(
        t, "stage_separation", f"Separação: {stage.name}.", {"mass_kg": stage.jettison_mass_kg}
    )

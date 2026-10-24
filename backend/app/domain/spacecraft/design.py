"""Avaliação de engenharia de uma espaçonave montada a partir do catálogo.

Convenção de estágios: `stages[0]` queima primeiro e é descartado ao esgotar;
o último estágio é a espaçonave propriamente dita e nunca é descartado.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from app.domain.propulsion.rocket import burn_duration, combined_isp, delta_v
from app.domain.spacecraft.catalog import Component

Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class PartRef:
    component_id: str
    quantity: int = 1
    propellant_kg: float | None = None  # por unidade; padrão = capacidade do tanque


@dataclass(frozen=True, slots=True)
class StageSpec:
    name: str
    parts: tuple[PartRef, ...]


@dataclass(frozen=True, slots=True)
class Issue:
    severity: Severity
    code: str
    message: str
    stage: int | None = None


@dataclass(frozen=True, slots=True)
class StagePerformance:
    name: str
    dry_mass_kg: float
    propellant_kg: float
    thrust_n: float
    isp_s: float | None
    delta_v_ms: float
    burn_time_s: float | None
    initial_mass_kg: float  # massa do veículo (este + superiores) ao ignitar este estágio
    final_mass_kg: float  # ao fim da queima, antes do descarte


@dataclass(frozen=True, slots=True)
class DesignReport:
    stages: tuple[StagePerformance, ...]
    dry_mass_kg: float
    propellant_kg: float
    wet_mass_kg: float
    final_mass_kg: float  # massa do último estágio após esgotar o propelente
    total_delta_v_ms: float
    power_generation_w: float
    power_consumption_w: float
    power_margin_w: float
    battery_capacity_wh: float
    cost_musd: float
    reliability: float
    contains_fictional: bool
    issues: tuple[Issue, ...] = field(default_factory=tuple)

    @property
    def valid(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


@dataclass(slots=True)
class _StageAgg:
    dry: float = 0.0
    prop: float = 0.0
    engines: list[tuple[float, float, str]] = field(default_factory=list)  # F, Isp, propelente
    tank_props: dict[str, float] = field(default_factory=dict)


MAX_STAGES = 4
MAX_PARTS_PER_STAGE = 64
MAX_QUANTITY = 32


def evaluate_design(stages: list[StageSpec], catalog: dict[str, Component]) -> DesignReport:
    issues: list[Issue] = []
    if not stages:
        raise ValueError("A espaçonave precisa de ao menos um estágio.")
    if len(stages) > MAX_STAGES:
        raise ValueError(f"No máximo {MAX_STAGES} estágios.")

    aggs: list[_StageAgg] = []
    gen = cons = batt = cost = 0.0
    rel = 1.0
    fictional = False
    categories: set[str] = set()
    final_categories: set[str] = set()
    has_transmitter = False
    has_antenna = False

    for si, stage in enumerate(stages):
        if len(stage.parts) > MAX_PARTS_PER_STAGE:
            raise ValueError("Componentes demais em um estágio.")
        agg = _StageAgg()
        is_final = si == len(stages) - 1
        for part in stage.parts:
            comp = catalog.get(part.component_id)
            if comp is None:
                raise ValueError(f"Componente desconhecido: {part.component_id}")
            if not 1 <= part.quantity <= MAX_QUANTITY:
                raise ValueError("Quantidade fora do intervalo permitido.")
            q = part.quantity
            agg.dry += comp.mass_kg * q
            cost += comp.cost_musd * q
            rel *= comp.reliability**q
            fictional = fictional or comp.fictional
            categories.add(comp.category)
            if is_final:
                final_categories.add(comp.category)
            if comp.category == "propulsion_engine":
                p = comp.params
                agg.engines.extend([(float(p["thrust_n"]), float(p["isp_s"]), p["propellant"])] * q)
            elif comp.category == "propulsion_tank":
                cap = float(comp.params["capacity_kg"])
                load = cap if part.propellant_kg is None else part.propellant_kg
                if not 0 <= load <= cap:
                    raise ValueError(f"Carga de propelente fora da capacidade de {comp.name}.")
                kind = comp.params["propellant"]
                agg.tank_props[kind] = agg.tank_props.get(kind, 0.0) + load * q
                agg.prop += load * q
            # Energia: só os componentes que permanecem em voo contam no balanço de cruzeiro.
            if is_final:
                gen += comp.power_generation_w * q
                cons += comp.power_consumption_w * q
                if comp.category == "power_battery":
                    batt += float(comp.params["capacity_wh"]) * q
                if comp.category == "comms":
                    if comp.params.get("transmitter"):
                        has_transmitter = True
                    else:
                        has_antenna = True
        _check_stage_propulsion(si, agg, issues)
        aggs.append(agg)

    # Delta-v por estágio, de cima para baixo em massa.
    upper_mass = [0.0] * len(aggs)
    acc = 0.0
    for i in range(len(aggs) - 1, -1, -1):
        upper_mass[i] = acc
        acc += aggs[i].dry + aggs[i].prop
    wet = acc

    perf: list[StagePerformance] = []
    total_dv = 0.0
    for i, agg in enumerate(aggs):
        m0 = agg.dry + agg.prop + upper_mass[i]
        usable = [(f, isp) for f, isp, kind in agg.engines if agg.tank_props.get(kind, 0) > 0]
        burnable = _usable_propellant(agg)
        mf = m0 - burnable
        isp: float | None
        bt: float | None
        if usable and burnable > 0:
            isp = combined_isp(usable)
            thrust = sum(f for f, _ in usable)
            dv = delta_v(isp, m0, mf)
            bt = burn_duration(thrust, isp, burnable)
        else:
            isp = combined_isp(usable) if usable else None
            thrust = sum(f for f, _ in usable)
            dv, bt = 0.0, None
        total_dv += dv
        perf.append(
            StagePerformance(stages[i].name, agg.dry, burnable, thrust, isp, dv, bt, m0, mf)
        )

    if "avionics" not in final_categories:
        issues.append(Issue("error", "no_avionics", "Sem computador de bordo no estágio final."))
    if "power_solar" not in final_categories:
        issues.append(Issue("error", "no_power_source", "Sem geração de energia."))
    if not (has_transmitter and has_antenna):
        issues.append(
            Issue("error", "no_comms", "Comunicação incompleta: requer antena e transmissor.")
        )
    if "attitude" not in final_categories:
        issues.append(
            Issue("warning", "no_attitude", "Sem controle de atitude: apontamento livre.")
        )
    if "power_battery" not in final_categories:
        issues.append(Issue("warning", "no_battery", "Sem bateria: sem energia durante eclipses."))
    if "structure" not in final_categories:
        issues.append(Issue("error", "no_structure", "Estágio final sem núcleo estrutural."))
    for i in range(len(stages) - 1):
        if not any(
            p.component_id in catalog and catalog[p.component_id].params.get("separator")
            for p in stages[i].parts
        ):
            issues.append(
                Issue("error", "no_separator", "Estágio descartável sem anel de separação.", i)
            )
    margin = gen - cons
    if gen > 0 and margin < 0:
        issues.append(
            Issue(
                "error",
                "power_deficit",
                f"Consumo excede geração em {-margin:.0f} W.",
            )
        )

    dry_total = sum(a.dry for a in aggs)
    prop_total = sum(a.prop for a in aggs)
    final_mass = aggs[-1].dry + aggs[-1].prop - _usable_propellant(aggs[-1])
    if not math.isfinite(total_dv):
        raise ValueError("Delta-v não finito.")

    return DesignReport(
        stages=tuple(perf),
        dry_mass_kg=dry_total,
        propellant_kg=prop_total,
        wet_mass_kg=wet,
        final_mass_kg=final_mass,
        total_delta_v_ms=total_dv,
        power_generation_w=gen,
        power_consumption_w=cons,
        power_margin_w=margin,
        battery_capacity_wh=batt,
        cost_musd=cost,
        reliability=rel,
        contains_fictional=fictional,
        issues=tuple(issues),
    )


def _check_stage_propulsion(si: int, agg: _StageAgg, issues: list[Issue]) -> None:
    engine_kinds = {kind for _, _, kind in agg.engines}
    for kind, mass in agg.tank_props.items():
        if mass > 0 and kind not in engine_kinds:
            issues.append(
                Issue("warning", "orphan_tank", f"Propelente '{kind}' sem motor compatível.", si)
            )
    for kind in engine_kinds:
        if agg.tank_props.get(kind, 0) <= 0:
            issues.append(
                Issue("error", "engine_without_propellant", f"Motor '{kind}' sem tanque.", si)
            )


def _usable_propellant(agg: _StageAgg) -> float:
    kinds = {kind for _, _, kind in agg.engines}
    return sum(m for kind, m in agg.tank_props.items() if kind in kinds)

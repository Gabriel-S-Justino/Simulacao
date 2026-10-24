import math

import pytest

from app.domain.constants import G0
from app.domain.spacecraft.design import PartRef, StageSpec, evaluate_design


def test_single_stage_mass_and_dv(catalog, single_stage) -> None:  # type: ignore[no-untyped-def]
    rep = evaluate_design(single_stage, catalog)
    assert rep.valid, rep.issues
    dry = sum(catalog[p.component_id].mass_kg * p.quantity for p in single_stage[0].parts)
    assert rep.dry_mass_kg == pytest.approx(dry)
    assert rep.propellant_kg == 150.0
    assert rep.total_delta_v_ms == pytest.approx(318 * G0 * math.log((dry + 150) / dry), rel=1e-12)


def test_staging_beats_naive_sum_and_is_sequential(catalog, two_stage) -> None:  # type: ignore[no-untyped-def]
    rep = evaluate_design(two_stage, catalog)
    assert rep.valid, rep.issues
    s0, s1 = rep.stages
    # m0 do estágio superior = sua própria massa seca + propelente (o inferior já foi descartado).
    assert s1.initial_mass_kg == pytest.approx(s1.dry_mass_kg + s1.propellant_kg)
    assert s0.final_mass_kg == pytest.approx(s0.initial_mass_kg - s0.propellant_kg)
    assert s0.initial_mass_kg == pytest.approx(rep.wet_mass_kg)
    assert rep.total_delta_v_ms == pytest.approx(s0.delta_v_ms + s1.delta_v_ms)
    # Estágio inferior carrega o superior: seu Δv é menor do que se voasse sozinho.
    own_m0 = s0.initial_mass_kg - s1.initial_mass_kg
    own_mf = s0.final_mass_kg - s1.initial_mass_kg
    alone = 318 * G0 * math.log(own_m0 / own_mf)
    assert s0.delta_v_ms < alone


def test_more_propellant_more_dv_more_mass(catalog, single_stage) -> None:  # type: ignore[no-untyped-def]
    base = evaluate_design(single_stage, catalog)
    lighter = [
        StageSpec(
            "Satélite",
            tuple(
                PartRef(p.component_id, p.quantity, 50.0)
                if p.component_id == "tank-biprop-150"
                else p
                for p in single_stage[0].parts
            ),
        )
    ]
    rep = evaluate_design(lighter, catalog)
    assert rep.total_delta_v_ms < base.total_delta_v_ms
    assert rep.wet_mass_kg == pytest.approx(base.wet_mass_kg - 100)


def test_power_deficit_is_error(catalog) -> None:  # type: ignore[no-untyped-def]
    parts = (
        PartRef("core-s"),
        PartRef("obc-1"),
        PartRef("sa-600"),
        PartRef("ant-lga"),
        PartRef("tx-x-20", 4),
        PartRef("cam-ms-25", 6),
    )
    rep = evaluate_design([StageSpec("S", parts)], catalog)
    codes = {i.code for i in rep.issues}
    assert "power_deficit" in codes and not rep.valid
    assert rep.power_margin_w < 0


def test_engine_without_matching_tank(catalog) -> None:  # type: ignore[no-untyped-def]
    parts = (PartRef("core-s"), PartRef("eng-biprop-400"), PartRef("tank-mono-40"))
    rep = evaluate_design([StageSpec("S", parts)], catalog)
    codes = {i.code for i in rep.issues}
    assert {"engine_without_propellant", "orphan_tank"} <= codes
    assert rep.total_delta_v_ms == 0.0


def test_missing_separator_flagged(catalog, two_stage) -> None:  # type: ignore[no-untyped-def]
    lower = StageSpec(
        "Inferior", tuple(p for p in two_stage[0].parts if p.component_id != "sep-ring")
    )
    rep = evaluate_design([lower, two_stage[1]], catalog)
    assert any(i.code == "no_separator" for i in rep.issues)


def test_unknown_component_rejected(catalog) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        evaluate_design([StageSpec("S", (PartRef("nope"),))], catalog)


def test_catalog_marks_fictional(catalog) -> None:  # type: ignore[no-untyped-def]
    assert all(c.fictional for c in catalog.values())

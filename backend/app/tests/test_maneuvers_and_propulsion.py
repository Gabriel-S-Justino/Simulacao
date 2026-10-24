import math

import pytest

from app.domain.constants import G0, MU_EARTH
from app.domain.orbital_mechanics.maneuvers import bi_elliptic, hohmann
from app.domain.propulsion.rocket import combined_isp, delta_v, propellant_for_dv


def test_hohmann_vallado_example_6_1() -> None:
    # Vallado, Fundamentals of Astrodynamics and Applications, 4ª ed., Exemplo 6-1:
    # r_i = 6569,4781 km, r_f = 42 159,4824 km → Δva = 2,457038 km/s, Δvb = 1,478187 km/s,
    # Δv total = 3,935224 km/s, τ = 5,256713 h. Tolerância: 1 mm/s e 0,1 s.
    tr = hohmann(6_569_478.1, 42_159_482.4, MU_EARTH)
    assert tr.dv1 == pytest.approx(2457.038, abs=1e-3)
    assert tr.dv2 == pytest.approx(1478.187, abs=1e-3)
    assert tr.total_dv == pytest.approx(3935.224, abs=2e-3)
    assert tr.transfer_time == pytest.approx(5.256713 * 3600, abs=0.1)


def test_hohmann_is_reversible() -> None:
    up = hohmann(7e6, 9e6, MU_EARTH)
    down = hohmann(9e6, 7e6, MU_EARTH)
    assert down.total_dv == pytest.approx(up.total_dv, rel=1e-14)
    assert down.dv1 < 0 and down.dv2 < 0


def test_bi_elliptic_beats_hohmann_for_large_ratio() -> None:
    # Para r2/r1 > 15,58 a bi-elíptica (rb → grande) é mais econômica.
    r1, r2 = 7e6, 20 * 7e6
    h = hohmann(r1, r2, MU_EARTH).total_dv
    d1, d2, d3, _ = bi_elliptic(r1, r2, 60 * 7e6, MU_EARTH)
    assert abs(d1) + abs(d2) + abs(d3) < h


def test_tsiolkovsky_identity() -> None:
    assert delta_v(300, math.e, 1.0) == pytest.approx(300 * G0, rel=1e-15)
    m0 = 500.0
    used = propellant_for_dv(320, m0, 1000.0)
    assert delta_v(320, m0, m0 - used) == pytest.approx(1000.0, rel=1e-12)


def test_combined_isp_is_mass_flow_weighted() -> None:
    assert combined_isp([(100, 300), (100, 300)]) == pytest.approx(300)
    isp = combined_isp([(400, 318), (22, 230)])
    assert 230 < isp < 318
    assert isp == pytest.approx(422 / (400 / 318 + 22 / 230))


@pytest.mark.parametrize("bad", [(0, 10, 5), (300, 5, 10), (300, -1, -2)])
def test_tsiolkovsky_rejects_invalid(bad: tuple[float, float, float]) -> None:
    with pytest.raises(ValueError):
        delta_v(*bad)

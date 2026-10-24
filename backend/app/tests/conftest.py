import pytest

from app.domain.spacecraft.catalog import load_catalog
from app.domain.spacecraft.design import PartRef, StageSpec


@pytest.fixture
def catalog():  # type: ignore[no-untyped-def]
    return load_catalog().by_id()


def bus_parts() -> tuple[PartRef, ...]:
    return (
        PartRef("core-s"),
        PartRef("obc-1"),
        PartRef("sa-600"),
        PartRef("bat-1kwh"),
        PartRef("ant-lga"),
        PartRef("tx-x-20"),
        PartRef("rw-set-4"),
        PartRef("st-1"),
        PartRef("thermal-ctl"),
    )


@pytest.fixture
def single_stage() -> list[StageSpec]:
    return [
        StageSpec(
            "Satélite",
            (*bus_parts(), PartRef("eng-biprop-400"), PartRef("tank-biprop-150")),
        )
    ]


@pytest.fixture
def two_stage() -> list[StageSpec]:
    return [
        StageSpec(
            "Estágio de transferência",
            (PartRef("eng-biprop-400"), PartRef("tank-biprop-150", 2), PartRef("sep-ring")),
        ),
        StageSpec(
            "Satélite",
            (*bus_parts(), PartRef("eng-mono-22", 4), PartRef("tank-mono-40")),
        ),
    ]

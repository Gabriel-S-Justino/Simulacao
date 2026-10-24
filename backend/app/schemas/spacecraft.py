from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.spacecraft.design import (
    DesignReport,
    PartRef,
    StageSpec,
)


class PartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    component_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=32)
    propellant_kg: float | None = Field(default=None, ge=0, le=1e6)


class StageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=64)
    parts: list[PartIn] = Field(max_length=64)


class DesignIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stages: list[StageIn] = Field(min_length=1, max_length=4)

    def to_domain(self) -> list[StageSpec]:
        return [
            StageSpec(
                s.name, tuple(PartRef(p.component_id, p.quantity, p.propellant_kg) for p in s.parts)
            )
            for s in self.stages
        ]


class IssueOut(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    stage: int | None = None


class StagePerformanceOut(BaseModel):
    name: str
    dry_mass_kg: float
    propellant_kg: float
    thrust_n: float
    isp_s: float | None
    delta_v_ms: float
    burn_time_s: float | None
    initial_mass_kg: float
    final_mass_kg: float


class DesignReportOut(BaseModel):
    valid: bool
    stages: list[StagePerformanceOut]
    dry_mass_kg: float
    propellant_kg: float
    wet_mass_kg: float
    final_mass_kg: float
    total_delta_v_ms: float
    power_generation_w: float
    power_consumption_w: float
    power_margin_w: float
    battery_capacity_wh: float
    cost_musd: float
    reliability: float
    contains_fictional: bool
    issues: list[IssueOut]

    @classmethod
    def from_domain(cls, r: DesignReport) -> "DesignReportOut":
        return cls(
            valid=r.valid,
            stages=[StagePerformanceOut.model_validate(_asdict(s)) for s in r.stages],
            dry_mass_kg=r.dry_mass_kg,
            propellant_kg=r.propellant_kg,
            wet_mass_kg=r.wet_mass_kg,
            final_mass_kg=r.final_mass_kg,
            total_delta_v_ms=r.total_delta_v_ms,
            power_generation_w=r.power_generation_w,
            power_consumption_w=r.power_consumption_w,
            power_margin_w=r.power_margin_w,
            battery_capacity_wh=r.battery_capacity_wh,
            cost_musd=r.cost_musd,
            reliability=r.reliability,
            contains_fictional=r.contains_fictional,
            issues=[IssueOut.model_validate(_asdict(i)) for i in r.issues],
        )


def _asdict(obj: object) -> dict[str, object]:
    from dataclasses import asdict, is_dataclass

    assert is_dataclass(obj) and not isinstance(obj, type)
    return asdict(obj)

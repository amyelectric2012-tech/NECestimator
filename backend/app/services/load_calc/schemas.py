from typing import Literal

from pydantic import BaseModel, Field


class ApplianceInput(BaseModel):
    name: str
    rating_kw: float | None = None
    rating_va: float | None = None
    is_fastened: bool = True
    is_continuous: bool = False
    quantity: int = 1


class LoadCalcRequest(BaseModel):
    project_type: Literal["single_family", "multi_family", "adu", "duplex"] = "single_family"
    floor_area_sqft: float = Field(..., gt=0)
    num_units: int = Field(1, ge=1)
    appliances: list[ApplianceInput] = []
    hvac_cooling_va: float = 0.0
    hvac_heating_va: float = 0.0
    include_both_methods: bool = True


class LoadLineItem(BaseModel):
    description: str
    connected_va: float
    demand_factor: float | None = None
    demand_va: float
    notes: str | None = None


class LoadCalcResult(BaseModel):
    method: str
    line_items: list[LoadLineItem]
    total_connected_va: float
    total_demand_va: float
    neutral_va: float
    recommended_service_amps: int
    calculation_notes: list[str] = []

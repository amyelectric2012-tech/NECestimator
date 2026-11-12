from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    project_type: str = "single_family"
    floor_area_sqft: float = Field(0.0, ge=0)
    num_units: int = Field(1, ge=1)
    small_appliance_circuits: int = Field(2, ge=0, le=20)
    laundry_circuits: int = Field(1, ge=0, le=10)
    appliances: list[dict[str, Any]] = []
    range_count: int = 0
    range_kw_each: float = 0.0
    range_ratings_kw: list[float] = []
    dryer_count: int = 0
    dryer_kw_each: float = 5.0
    dryer_ratings_kw: list[float] = []
    hvac: dict[str, Any] = {}
    largest_motor_va: float = 0.0
    existing_service_amps: float | None = None
    jurisdiction: str | None = None
    nec_edition: str = "2017"
    labor_rate: float = 85.0


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    project_type: str | None = None
    status: str | None = None
    floor_area_sqft: float | None = Field(None, ge=0)
    num_units: int | None = Field(None, ge=1)
    small_appliance_circuits: int | None = Field(None, ge=0, le=20)
    laundry_circuits: int | None = Field(None, ge=0, le=10)
    appliances: list[dict[str, Any]] | None = None
    range_count: int | None = None
    range_kw_each: float | None = None
    range_ratings_kw: list[float] | None = None
    dryer_count: int | None = None
    dryer_kw_each: float | None = None
    dryer_ratings_kw: list[float] | None = None
    hvac: dict[str, Any] | None = None
    largest_motor_va: float | None = None
    existing_service_amps: float | None = None
    client_id: str | None = None
    jurisdiction: str | None = None
    nec_edition: str | None = None
    labor_rate: float | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    project_type: str
    status: str
    floor_area_sqft: float
    num_units: int
    small_appliance_circuits: int
    laundry_circuits: int
    appliances: list[dict[str, Any]] = []
    range_count: int
    range_kw_each: float
    range_ratings_kw: list[float] = []
    dryer_count: int
    dryer_kw_each: float
    dryer_ratings_kw: list[float] = []
    hvac: dict[str, Any] = {}
    largest_motor_va: float
    existing_service_amps: float | None = None
    client_id: str | None = None
    jurisdiction: str | None = None
    nec_edition: str = "2017"
    labor_rate: float = 85.0
    owner_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MaterialCreate(BaseModel):
    sku: str | None = None
    name: str
    category: str | None = None
    unit: str = "ea"
    unit_cost: float = Field(0.0, ge=0)
    labor_hours: float = Field(0.0, ge=0)
    labor_category: str = "rough_in"
    description: str | None = None


class MaterialUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    category: str | None = None
    unit: str | None = None
    unit_cost: float | None = Field(None, ge=0)
    labor_hours: float | None = Field(None, ge=0)
    labor_category: str | None = None
    description: str | None = None


class MaterialOut(BaseModel):
    id: str
    sku: str | None = None
    name: str
    category: str | None = None
    unit: str
    unit_cost: float
    labor_hours: float
    labor_category: str
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class EstimateCreate(BaseModel):
    name: str = "Bid"
    markup_pct: float = 0.10
    contingency_pct: float = 0.05
    tax_pct: float = 0.0
    overhead_pct: float = 0.10
    scope_of_work: str | None = None
    assumptions: str | None = None
    line_items: list[dict[str, Any]] = []
    labor_summary: dict[str, Any] = {}
    status: str | None = "draft"
    probability: float | None = None
    follow_up_date: datetime | None = None
    next_action: str | None = None
    crm_notes: str | None = None


class EstimateUpdate(BaseModel):
    name: str | None = None
    markup_pct: float | None = None
    contingency_pct: float | None = None
    tax_pct: float | None = None
    overhead_pct: float | None = None
    scope_of_work: str | None = None
    assumptions: str | None = None
    line_items: list[dict[str, Any]] | None = None
    labor_summary: dict[str, Any] | None = None
    status: str | None = None
    probability: float | None = None
    follow_up_date: datetime | None = None
    next_action: str | None = None
    crm_notes: str | None = None
    last_contacted_at: datetime | None = None


class EstimateOut(BaseModel):
    id: str
    project_id: str
    client_id: str | None = None
    name: str
    markup_pct: float
    contingency_pct: float
    tax_pct: float
    overhead_pct: float = 0.10
    scope_of_work: str | None = None
    assumptions: str | None = None
    line_items: list[dict[str, Any]] = []
    labor_summary: dict[str, Any] = {}
    total_materials: float
    total_labor_hours: float
    total_cost: float
    direct_cost: float = 0.0
    overhead_cost: float = 0.0
    contingency_cost: float = 0.0
    markup_cost: float = 0.0
    tax_cost: float = 0.0
    profit: float = 0.0
    gross_margin: float = 0.0
    pdf_path: str | None = None
    status: str = "draft"
    probability: float | None = None
    follow_up_date: datetime | None = None
    next_action: str | None = None
    crm_notes: str | None = None
    last_contacted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EstimateActivityCreate(BaseModel):
    activity_type: str = "note"
    body: str


class EstimateActivityOut(BaseModel):
    id: str
    estimate_id: str
    activity_type: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TakeoffItemBase(BaseModel):
    description: str
    category: str
    quantity: float = Field(..., gt=0)
    unit: str = "ea"
    unit_cost: Decimal = Field(..., ge=0)
    labor_hours: float = Field(0.0, ge=0)
    notes: str | None = None


class TakeoffItemCreate(TakeoffItemBase):
    material_id: UUID | None = None
    is_auto_generated: bool = False


class TakeoffItemUpdate(BaseModel):
    description: str | None = None
    category: str | None = None
    quantity: float | None = Field(None, gt=0)
    unit: str | None = None
    unit_cost: Decimal | None = Field(None, ge=0)
    labor_hours: float | None = Field(None, ge=0)
    notes: str | None = None


class TakeoffItemResponse(TakeoffItemBase):
    id: UUID
    project_id: UUID
    material_id: UUID | None
    is_auto_generated: bool
    total_material_cost: Decimal
    total_labor_hours: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TakeoffSummary(BaseModel):
    items: list[TakeoffItemResponse]
    total_material_cost: Decimal
    total_labor_hours: float
    labor_rate: Decimal = Decimal("85.00")
    total_labor_cost: Decimal
    subtotal: Decimal
    contingency_percent: float = 5.0
    contingency_amount: Decimal
    tax_percent: float = 0.0
    tax_amount: Decimal
    grand_total: Decimal

"""
NEC 2017 – Optional Method for Dwelling Units (220.82)
"""

from app.services.load_calc.helpers import (
    largest_motor_or_hvac,
    recommend_service_size,
    va_from_kw,
)
from app.services.load_calc.schemas import (
    ApplianceInput,
    LoadCalcRequest,
    LoadCalcResult,
    LoadLineItem,
)


def _get_appliance_va(app: ApplianceInput) -> float:
    if app.rating_va is not None:
        return app.rating_va * app.quantity
    if app.rating_kw is not None:
        return va_from_kw(app.rating_kw) * app.quantity
    return 0.0


def calculate_optional_82(data: LoadCalcRequest) -> LoadCalcResult:
    """
    220.82 Optional Calculation – Dwelling Unit
    Applicable when served by single 120/240V or 208Y/120V 3-wire service
    with ampacity of 100 A or greater.
    """
    line_items: list[LoadLineItem] = []
    notes: list[str] = [
        "Optional Method per NEC 220.82",
        "100% of the first 10 kVA + 40% of the remainder"
    ]

    lighting_va = data.floor_area_sqft * 3.0
    sa_laundry_va = 1500 * 2 + 1500

    appliance_total = 0.0
    for app in data.appliances:
        appliance_total += _get_appliance_va(app)

    hvac_va = largest_motor_or_hvac(data.hvac_heating_va, data.hvac_cooling_va)

    total_connected = lighting_va + sa_laundry_va + appliance_total + hvac_va

    first_10kva = min(total_connected, 10_000)
    remainder = max(total_connected - 10_000, 0)
    demand_va = first_10kva * 1.00 + remainder * 0.40

    line_items.append(LoadLineItem(
        description="General Lighting (3 VA/ft²)",
        connected_va=lighting_va,
        demand_va=0.0,
    ))
    line_items.append(LoadLineItem(
        description="Small-Appliance + Laundry Circuits",
        connected_va=sa_laundry_va,
        demand_va=0.0,
    ))
    line_items.append(LoadLineItem(
        description="Appliances (nameplate total)",
        connected_va=appliance_total,
        demand_va=0.0,
    ))
    if hvac_va > 0:
        line_items.append(LoadLineItem(
            description="HVAC (larger of Heating/Cooling)",
            connected_va=hvac_va,
            demand_va=0.0,
        ))

    line_items.append(LoadLineItem(
        description="Optional Method Demand (100% first 10 kVA + 40% remainder)",
        connected_va=total_connected,
        demand_factor=demand_va / total_connected if total_connected else 1.0,
        demand_va=demand_va,
        notes="Per 220.82(B)",
    ))

    neutral_va = demand_va * 0.70

    recommended_amps = recommend_service_size(demand_va)

    notes.append(f"Total connected: {total_connected:,.0f} VA")
    notes.append(f"Demand load: {demand_va:,.0f} VA")
    notes.append(f"Recommended service: {recommended_amps} A")

    return LoadCalcResult(
        method="optional_220_82",
        line_items=line_items,
        total_connected_va=round(total_connected, 1),
        total_demand_va=round(demand_va, 1),
        neutral_va=round(neutral_va, 1),
        recommended_service_amps=recommended_amps,
        calculation_notes=notes,
    )

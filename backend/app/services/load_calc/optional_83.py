"""
NEC 2017 – Optional Method for Existing Dwelling (220.83)
"""
from app.services.load_calc.helpers import (
    largest_motor_or_hvac,
    recommend_service_size,
    va_from_kw,
)
from app.services.load_calc.schemas import LoadCalcRequest, LoadCalcResult, LoadLineItem


def _get_appliance_va(app) -> float:
    if app.rating_va is not None:
        return app.rating_va * app.quantity
    if app.rating_kw is not None:
        return va_from_kw(app.rating_kw) * app.quantity
    return 0.0


def calculate_optional_83(data: LoadCalcRequest) -> LoadCalcResult:
    line_items: list[LoadLineItem] = []
    notes: list[str] = [
        "Optional Method per NEC 220.83 (Existing Dwelling)",
    ]

    lighting_va = data.floor_area_sqft * 3.0
    sa_laundry_va = 1500 * 2 + 1500

    appliance_total = 0.0
    for app in data.appliances:
        appliance_total += _get_appliance_va(app)

    hvac_va = largest_motor_or_hvac(data.hvac_heating_va, data.hvac_cooling_va)

    other_items = lighting_va + sa_laundry_va + appliance_total
    has_new_hvac = hvac_va > 0

    if has_new_hvac:
        if other_items <= 8000:
            other_demand = other_items
        else:
            other_demand = 8000 + 0.4 * (other_items - 8000)
        total_demand = other_demand + hvac_va
        notes.append("220.83(B): new HVAC installed; HVAC at 100%.")
    else:
        total_connected = other_items
        if total_connected <= 8000:
            total_demand = total_connected
        else:
            total_demand = 8000 + 0.4 * (total_connected - 8000)
        notes.append("220.83(A): no new HVAC.")

    line_items.append(LoadLineItem(
        description="Existing + new loads (first 8 kVA @ 100%, remainder @ 40%)",
        connected_va=other_items,
        demand_va=total_demand - (hvac_va if has_new_hvac else 0),
        notes="Per 220.83",
    ))
    if hvac_va > 0:
        line_items.append(LoadLineItem(
            description="HVAC (larger of Heating/Cooling) @ 100%",
            connected_va=hvac_va,
            demand_va=hvac_va,
        ))

    neutral_va = (lighting_va + sa_laundry_va + appliance_total) * 0.7 + (hvac_va * 0 if has_new_hvac else 0)
    # simplified neutral
    neutral_va = other_items * 0.7

    recommended_amps = recommend_service_size(total_demand)

    total_connected = other_items + (hvac_va if has_new_hvac else 0)
    notes.append(f"Total demand: {total_demand:,.0f} VA")
    notes.append(f"Recommended service: {recommended_amps} A")

    return LoadCalcResult(
        method="optional_220_83",
        line_items=line_items,
        total_connected_va=round(total_connected, 1),
        total_demand_va=round(total_demand, 1),
        neutral_va=round(neutral_va, 1),
        recommended_service_amps=recommended_amps,
        calculation_notes=notes,
    )

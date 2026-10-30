"""
NEC 2017 – Optional Method for Multifamily Dwellings (220.84)
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
from app.services.load_calc.tables import get_multifamily_demand_factor


def _get_appliance_va(app: ApplianceInput) -> float:
    if app.rating_va is not None:
        return app.rating_va * app.quantity
    if app.rating_kw is not None:
        return va_from_kw(app.rating_kw) * app.quantity
    return 0.0


def calculate_optional_84(data: LoadCalcRequest) -> LoadCalcResult:
    """
    220.84 Optional Calculation – Multifamily Dwelling
    Requires 3 or more units, each with electric cooking, and served by a single feeder/service.
    """
    line_items: list[LoadLineItem] = []
    notes: list[str] = [
        "Optional Method per NEC 220.84 (Multifamily)",
        f"Number of units: {data.num_units}"
    ]

    if data.num_units < 3:
        notes.append("Warning: 220.84 requires 3 or more dwelling units. Falling back to per-unit calculation.")

    lighting_per_unit = data.floor_area_sqft * 3.0
    sa_laundry_per_unit = 1500 * 2 + 1500
    appliances_per_unit = sum(_get_appliance_va(a) for a in data.appliances)
    hvac_per_unit = largest_motor_or_hvac(data.hvac_heating_va, data.hvac_cooling_va)

    connected_per_unit = lighting_per_unit + sa_laundry_per_unit + appliances_per_unit + hvac_per_unit
    total_connected = connected_per_unit * data.num_units

    demand_factor = get_multifamily_demand_factor(data.num_units)
    demand_va = total_connected * demand_factor

    line_items.append(LoadLineItem(
        description=f"Total Connected Load ({data.num_units} units)",
        connected_va=total_connected,
        demand_factor=demand_factor,
        demand_va=demand_va,
        notes=f"Table 220.84 demand factor = {demand_factor:.0%}",
    ))

    neutral_va = demand_va * 0.70
    recommended_amps = recommend_service_size(demand_va)

    notes.append(f"Demand factor (Table 220.84): {demand_factor:.0%}")
    notes.append(f"Demand load: {demand_va:,.0f} VA")
    notes.append(f"Recommended service: {recommended_amps} A")

    return LoadCalcResult(
        method="optional_220_84",
        line_items=line_items,
        total_connected_va=round(total_connected, 1),
        total_demand_va=round(demand_va, 1),
        neutral_va=round(neutral_va, 1),
        recommended_service_amps=recommended_amps,
        calculation_notes=notes,
    )

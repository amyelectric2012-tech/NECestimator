"""
NEC 2017 – Standard Method (Article 220 Part III)
"""

from app.services.load_calc.helpers import (
    apply_continuous_factor,
    calculate_neutral_load,
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
from app.services.load_calc.tables import (
    apply_appliance_demand,
    apply_lighting_demand_factors,
    get_dryer_demand,
    get_range_demand,
)


def _get_appliance_va(app: ApplianceInput) -> float:
    if app.rating_va is not None:
        return app.rating_va * app.quantity
    if app.rating_kw is not None:
        return va_from_kw(app.rating_kw) * app.quantity
    return 0.0


def calculate_standard(data: LoadCalcRequest) -> LoadCalcResult:
    line_items: list[LoadLineItem] = []
    notes: list[str] = []

    # -------------------------------------------------------
    # 1. General Lighting (220.12)
    # -------------------------------------------------------
    lighting_va = data.floor_area_sqft * 3.0
    line_items.append(LoadLineItem(
        description=f"General Lighting ({data.floor_area_sqft:.0f} ft² × 3 VA/ft²)",
        connected_va=lighting_va,
        demand_va=0.0,
    ))

    # -------------------------------------------------------
    # 2. Small-Appliance + Laundry (220.52)
    # -------------------------------------------------------
    sa_va = 1500.0 * 2
    laundry_va = 1500.0
    sa_laundry_va = sa_va + laundry_va

    line_items.append(LoadLineItem(
        description="Small-Appliance Circuits (2 × 1500 VA)",
        connected_va=sa_va,
        demand_va=0.0,
    ))
    line_items.append(LoadLineItem(
        description="Laundry Circuit (1500 VA)",
        connected_va=laundry_va,
        demand_va=0.0,
    ))

    # -------------------------------------------------------
    # 3. Apply Table 220.42 demand factors
    # -------------------------------------------------------
    combined_lighting = lighting_va + sa_laundry_va
    lighting_demand = apply_lighting_demand_factors(combined_lighting)

    line_items.append(LoadLineItem(
        description="Lighting + SA + Laundry after Table 220.42 Demand Factors",
        connected_va=combined_lighting,
        demand_factor=lighting_demand / combined_lighting if combined_lighting else 1.0,
        demand_va=lighting_demand,
        notes="First 3000 VA @ 100%, next @ 35%, remainder @ 25%",
    ))

    # -------------------------------------------------------
    # 4. Classify appliances
    # -------------------------------------------------------
    range_va = 0.0
    dryer_va = 0.0
    other_fastened_va = 0.0
    other_count = 0
    continuous_va = 0.0

    for app in data.appliances:
        va = _get_appliance_va(app)
        name_lower = app.name.lower()

        if "range" in name_lower or "oven" in name_lower or "cooktop" in name_lower:
            kw = (app.rating_kw or (va / 1000))
            range_va += get_range_demand(kw, app.quantity)
            notes.append(f"Range/Oven: {app.name} → Table 220.55")
        elif "dryer" in name_lower:
            kw = app.rating_kw or 5.0
            dryer_va += get_dryer_demand(kw, app.quantity)
            notes.append(f"Dryer: {app.name} → Table 220.54")
        else:
            if app.is_fastened:
                other_fastened_va += va
                other_count += app.quantity
            if app.is_continuous:
                continuous_va += apply_continuous_factor(va)

    if range_va > 0:
        line_items.append(LoadLineItem(
            description="Electric Range(s) – Table 220.55",
            connected_va=range_va,
            demand_va=range_va,
        ))

    if dryer_va > 0:
        line_items.append(LoadLineItem(
            description="Electric Dryer(s) – Table 220.54",
            connected_va=dryer_va,
            demand_va=dryer_va,
        ))

    if other_fastened_va > 0:
        demand_other = apply_appliance_demand(other_count, other_fastened_va)
        factor = 0.75 if other_count >= 4 else 1.0
        line_items.append(LoadLineItem(
            description=f"Other Fastened Appliances ({other_count} units)",
            connected_va=other_fastened_va,
            demand_factor=factor,
            demand_va=demand_other,
            notes="75% demand factor applied if 4 or more (220.53)" if other_count >= 4 else None,
        ))
        other_fastened_va = demand_other

    # -------------------------------------------------------
    # 5. HVAC – Noncoincident Loads (220.60)
    # -------------------------------------------------------
    hvac_va = largest_motor_or_hvac(data.hvac_heating_va, data.hvac_cooling_va)
    if hvac_va > 0:
        hvac_demand = apply_continuous_factor(hvac_va, is_continuous=True)
        line_items.append(LoadLineItem(
            description="HVAC (larger of Heating / Cooling) @ 125%",
            connected_va=hvac_va,
            demand_factor=1.25,
            demand_va=hvac_demand,
            notes="Noncoincident loads – 220.60 + continuous factor",
        ))
    else:
        hvac_demand = 0.0

    # -------------------------------------------------------
    # 6. Totals
    # -------------------------------------------------------
    total_connected = (
        lighting_va + sa_laundry_va + range_va + dryer_va +
        sum(_get_appliance_va(a) for a in data.appliances) + hvac_va
    )

    total_demand = (
        lighting_demand +
        range_va +
        dryer_va +
        other_fastened_va +
        hvac_demand
    )

    # -------------------------------------------------------
    # 7. Neutral (220.61)
    # -------------------------------------------------------
    neutral = calculate_neutral_load(
        lighting_and_appliance_va=lighting_demand + other_fastened_va,
        range_va=range_va,
        dryer_va=dryer_va,
    )

    # -------------------------------------------------------
    # 8. Service size
    # -------------------------------------------------------
    recommended_amps = recommend_service_size(total_demand)

    notes.append(f"Calculated demand load: {total_demand:,.0f} VA")
    notes.append(f"Recommended service size: {recommended_amps} A")

    return LoadCalcResult(
        method="standard",
        line_items=line_items,
        total_connected_va=round(total_connected, 1),
        total_demand_va=round(total_demand, 1),
        neutral_va=round(neutral, 1),
        recommended_service_amps=recommended_amps,
        calculation_notes=notes,
    )

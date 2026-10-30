"""
NEC 2017 Article 220 Tables and Demand Factor Functions
"""



def apply_lighting_demand_factors(va: float, occupancy: str = "dwelling") -> float:
    """
    Table 220.42 – Lighting Load Demand Factors
    Currently implements Dwelling Units (most common).
    """
    if occupancy != "dwelling":
        # For now we only fully support dwellings
        return va

    if va <= 3000:
        return va

    demand = 3000 * 1.00  # First 3000 VA at 100%

    if va <= 120_000:
        demand += (va - 3000) * 0.35
        return demand

    # Over 120,000 VA
    demand += (120_000 - 3000) * 0.35
    demand += (va - 120_000) * 0.25
    return demand


def get_range_demand(kw: float, num_ranges: int = 1) -> float:
    """
    Table 220.55 – Household Electric Ranges
    Uses Column C (most common case) + Note 1 for ranges > 12 kW.
    Returns demand in VA.
    """
    if num_ranges < 1:
        return 0.0

    # Base demand from Column C (for ranges ≤ 12 kW)
    # Simplified lookup for 1–5 ranges (most common residential cases)
    column_c = {
        1: 8.0,
        2: 11.0,
        3: 14.0,
        4: 17.0,
        5: 20.0,
        6: 21.0,
        7: 22.0,
        8: 23.0,
        9: 24.0,
        10: 25.0,
    }

    if num_ranges <= 10:
        base_kw = column_c.get(num_ranges, 25.0)
    elif num_ranges <= 40:
        base_kw = 15 + (num_ranges)  # approximate per Note
    else:
        base_kw = 25 + (num_ranges - 40) * 0.75

    # Note 1: Over 12 kW through 27 kW – increase 5% for each kW over 12
    if kw > 12:
        excess = min(kw - 12, 15)  # up to 27 kW
        increase_factor = 1 + (0.05 * excess)
        base_kw *= increase_factor

    return base_kw * 1000  # convert kW to VA


def get_dryer_demand(kw: float = 5.0, num_dryers: int = 1) -> float:
    """
    Table 220.54 – Household Electric Clothes Dryers
    Minimum 5000 W per dryer.
    """
    if num_dryers < 1:
        return 0.0

    # Use the larger of nameplate or 5 kW
    load_per_dryer = max(kw, 5.0) * 1000  # VA

    demand_factors = {
        1: 1.00, 2: 1.00, 3: 1.00, 4: 1.00,
        5: 0.85, 6: 0.75, 7: 0.65, 8: 0.60,
        9: 0.55, 10: 0.50,
    }

    if num_dryers <= 10:
        factor = demand_factors.get(num_dryers, 0.50)
    elif num_dryers <= 23:
        factor = 0.47 - (0.01 * (num_dryers - 11))
    elif num_dryers <= 42:
        factor = 0.35 - (0.005 * (num_dryers - 24))
    else:
        factor = 0.25

    return load_per_dryer * num_dryers * factor


def get_multifamily_demand_factor(num_units: int) -> float:
    """
    Table 220.84 – Optional Calculation for Multifamily Dwellings
    """
    if num_units < 3:
        return 1.0

    factors = {
        3: 0.45, 4: 0.45, 5: 0.45,
        6: 0.44, 7: 0.44,
        8: 0.43, 9: 0.43, 10: 0.43,
        11: 0.42,
        12: 0.41, 13: 0.41,
        14: 0.40, 15: 0.40,
        16: 0.39, 17: 0.39,
        18: 0.38, 19: 0.38, 20: 0.38,
        21: 0.37,
        22: 0.36, 23: 0.36,
        24: 0.35, 25: 0.35,
    }

    if num_units in factors:
        return factors[num_units]
    if num_units <= 30:
        return 0.33
    if num_units <= 40:
        return 0.31
    if num_units <= 50:
        return 0.26
    return 0.23  # 62 and over


def apply_appliance_demand(num_appliances: int, total_va: float) -> float:
    """
    220.53 – Appliance Load – Dwelling Unit(s)
    75% demand factor when 4 or more fastened-in-place appliances
    (excluding ranges, dryers, HVAC).
    """
    if num_appliances >= 4:
        return total_va * 0.75
    return total_va

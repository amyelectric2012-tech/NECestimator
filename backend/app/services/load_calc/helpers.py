"""
Shared helper functions for load calculations
"""

import math


def va_from_kw(kw: float) -> float:
    """Convert kW to VA (assuming PF = 1.0 for residential loads)."""
    return kw * 1000


def apply_continuous_factor(va: float, is_continuous: bool = True) -> float:
    """
    Continuous loads are calculated at 125% (210.19(A), 215.2, 230.42).
    """
    if is_continuous:
        return va * 1.25
    return va


def recommend_service_size(demand_va: float, voltage: float = 240.0) -> int:
    """
    Recommend standard service size (amps) with reasonable headroom.
    Common residential sizes: 100, 125, 150, 200, 225, 400 A
    """
    demand_amps = demand_va / voltage

    standard_sizes = [100, 125, 150, 200, 225, 400, 600, 800, 1000, 1200]

    for size in standard_sizes:
        # Leave ~20% headroom when possible
        if demand_amps <= size * 0.80:
            return size

    # Fallback: round up to next 50 A
    return int(math.ceil(demand_amps / 50) * 50)


def calculate_neutral_load(
    lighting_and_appliance_va: float,
    range_va: float = 0,
    dryer_va: float = 0,
    max_unbalanced_va: float | None = None,
) -> float:
    """
    Simplified neutral calculation per 220.61.
    - Lighting & appliances: full
    - Ranges & dryers: 70% of the demand load (permitted reduction)
    """
    neutral = lighting_and_appliance_va

    # 220.61(B) – permitted reduction for ranges and dryers
    neutral += (range_va + dryer_va) * 0.70

    if max_unbalanced_va is not None:
        neutral = max(neutral, max_unbalanced_va)

    return neutral


def largest_motor_or_hvac(heating_va: float, cooling_va: float) -> float:
    """
    220.60 – Noncoincident Loads.
    Use the largest load that will be used at one time.
    """
    return max(heating_va, cooling_va)


def format_va(va: float) -> str:
    """Nice formatting for reports."""
    if va >= 1000:
        return f"{va/1000:.2f} kVA"
    return f"{va:.0f} VA"

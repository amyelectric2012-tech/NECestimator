"""NEC 2017 Article 220 load calculation engine (residential)."""
from dataclasses import dataclass, field
from typing import Literal

STANDARD_SERVICE_SIZES = [60, 100, 125, 150, 200, 225, 250, 300, 350, 400, 450, 500, 600, 800, 1000]


@dataclass
class Appliance:
    name: str
    va: float = 0.0
    fastened: bool = True


@dataclass
class HVAC:
    cooling_va: float = 0.0
    heating_va: float = 0.0
    heat_pump: bool = False
    supplemental_heat_va: float = 0.0
    space_heating_units: int = 1
    thermal_storage: bool = False


@dataclass
class ProjectInput:
    project_type: Literal["single_family", "multi_family", "adu"] = "single_family"
    floor_area_sqft: float = 0.0  # per dwelling unit
    num_units: int = 1
    small_appliance_circuits: int = 2
    laundry_circuits: int = 1
    appliances: list[Appliance] = field(default_factory=list)
    range_count: int = 0
    range_kw_each: float = 0.0
    range_ratings_kw: list[float] = field(default_factory=list)
    dryer_count: int = 0
    dryer_kw_each: float = 5.0
    dryer_ratings_kw: list[float] = field(default_factory=list)
    hvac: HVAC = field(default_factory=HVAC)
    largest_motor_va: float = 0.0
    existing_service_amps: float | None = None


@dataclass
class LoadResult:
    method: str
    general_lighting_va: float = 0.0
    small_appliance_va: float = 0.0
    laundry_va: float = 0.0
    lighting_load_va: float = 0.0
    lighting_demand_va: float = 0.0
    fastened_appliances_va: float = 0.0
    fastened_demand_va: float = 0.0
    range_connected_va: float = 0.0
    range_demand_va: float = 0.0
    dryer_connected_va: float = 0.0
    dryer_demand_va: float = 0.0
    hvac_va: float = 0.0
    motor_adder_va: float = 0.0
    total_va: float = 0.0
    total_amps: float = 0.0
    neutral_va: float = 0.0
    neutral_amps: float = 0.0
    recommended_service_amps: int = 0
    sufficient_existing: bool | None = None
    breakdown: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# ---------- helpers ----------

def lighting_demand_dwell(va: float) -> float:
    """Table 220.42 dwelling units."""
    if va <= 3000:
        return va
    if va <= 120000:
        return 3000 + 0.35 * (va - 3000)
    return 3000 + 0.35 * 117000 + 0.25 * (va - 120000)


def dryer_demand_pct(n: int) -> float:
    if n <= 0:
        return 0.0
    if n <= 4:
        return 1.0
    if n == 5:
        return 0.85
    if n == 6:
        return 0.75
    if n == 7:
        return 0.65
    if n == 8:
        return 0.60
    if n == 9:
        return 0.55
    if n == 10:
        return 0.50
    if n == 11:
        return 0.47
    if 12 <= n <= 23:
        return 0.47 - 0.01 * (n - 11)
    if 24 <= n <= 42:
        return 0.35 - 0.005 * (n - 23)
    return 0.25


def dryer_demand(va_list: list[float]) -> float:
    n = len(va_list)
    if n == 0:
        return 0.0
    total = sum(va_list)
    return total * dryer_demand_pct(n)


_RANGE_BASE = {1: 8, 2: 11, 3: 14, 4: 17, 5: 20, 6: 21, 7: 22, 8: 23, 9: 24, 10: 25,
               11: 26, 12: 27, 13: 28, 14: 29, 15: 30, 16: 31, 17: 32, 18: 33, 19: 34,
               20: 35, 21: 36, 22: 37, 23: 38, 24: 39, 25: 40}


def range_demand(ratings_kw: list[float]) -> float:
    n = len(ratings_kw)
    if n == 0:
        return 0.0
    if n <= 25:
        base = _RANGE_BASE[n]
    elif 26 <= n <= 30:
        base = 15 + n
    elif 31 <= n <= 40:
        base = 25 + 0.75 * n
    elif 41 <= n <= 50:
        base = 25 + 0.5 * n
    else:
        base = 20 + 0.3 * n
    # Note 1/2: average rating (using 12 kW for any range < 12 kW)
    total_using_12 = sum(r if r > 12 else 12.0 for r in ratings_kw)
    avg = total_using_12 / n
    if avg > 12:
        kw_over = avg - 12.0
        whole = int(kw_over // 1)
        frac = kw_over - whole
        kw_major = whole + (1 if frac >= 0.5 else 0)
        kw_major = max(kw_major, 1)
        base = base * (1.0 + 0.05 * kw_major)
    return base * 1000.0


def recommend_service_amps(calculated_amps: float) -> int:
    target = calculated_amps * 1.10
    for s in STANDARD_SERVICE_SIZES:
        if s >= target:
            return s
    return STANDARD_SERVICE_SIZES[-1]


def _range_ratings(inp: ProjectInput) -> list[float]:
    if inp.range_ratings_kw:
        return list(inp.range_ratings_kw)
    if inp.range_count:
        r = inp.range_kw_each if inp.range_kw_each and inp.range_kw_each > 0 else 8.0
        return [r] * inp.range_count
    return []


def _dryer_va_list(inp: ProjectInput) -> list[float]:
    if inp.dryer_ratings_kw:
        return [max(r * 1000.0, 5000.0) for r in inp.dryer_ratings_kw]
    if inp.dryer_count:
        r = inp.dryer_kw_each if inp.dryer_kw_each and inp.dryer_kw_each > 0 else 5.0
        return [max(r * 1000.0, 5000.0)] * inp.dryer_count
    return []


def _fastened(inp: ProjectInput):
    items = [a for a in inp.appliances if a.fastened]
    connected = sum(a.va for a in items)
    count = len(items)
    if count >= 4:
        return connected, connected * 0.75, True
    return connected, connected, False


# ---------- Standard Method ----------

def standard_method(inp: ProjectInput) -> LoadResult:
    notes: list[str] = []
    gl = 3.0 * inp.floor_area_sqft
    small = 1500.0 * inp.small_appliance_circuits
    laundry = 1500.0 * inp.laundry_circuits
    lighting_load = gl + small + laundry
    lighting_demand = lighting_demand_dwell(lighting_load)

    fastened_connected, fastened_demand, reduced = _fastened(inp)
    if reduced:
        notes.append("NEC 220.53: 4+ fastened appliances, 75% demand applied.")

    rr = _range_ratings(inp)
    range_connected = sum(r * 1000.0 for r in rr)
    range_dem = range_demand(rr)

    dv = _dryer_va_list(inp)
    dryer_connected = sum(dv)
    dryer_dem = dryer_demand(dv)

    hvac = inp.hvac
    cooling = hvac.cooling_va
    # heating per 220.51 (100%) but noncoincident 220.60 -> largest
    heating = hvac.heating_va
    # if heat pump with supplemental
    if hvac.heat_pump and hvac.supplemental_heat_va > 0:
        supp = hvac.supplemental_heat_va * (0.65 if hvac.space_heating_units < 4 else 0.40)
        heating = hvac.cooling_va + supp  # compressor runs with supp? code allows prevention; simplify add
    hvac_va = max(cooling, heating)
    if cooling > 0 and heating > 0 and cooling != heating:
        notes.append("NEC 220.60: noncoincident loads - largest of heating/cooling used.")

    motor_adder = inp.largest_motor_va * 0.25
    if motor_adder > 0:
        notes.append("NEC 220.50/430.24: 25% of largest motor added.")

    total_va = lighting_demand + fastened_demand + range_dem + dryer_dem + hvac_va + motor_adder

    # neutral: ranges/dryers 70%
    neutral_va = lighting_demand + fastened_demand + range_dem * 0.7 + dryer_dem * 0.7
    # (HVAC 240V and motor excluded)

    total_amps = total_va / 240.0
    neutral_amps = neutral_va / 240.0
    recommended = recommend_service_amps(total_amps)

    sufficient = None
    if inp.existing_service_amps is not None:
        sufficient = total_amps <= inp.existing_service_amps

    return LoadResult(
        method="standard",
        general_lighting_va=gl,
        small_appliance_va=small,
        laundry_va=laundry,
        lighting_load_va=lighting_load,
        lighting_demand_va=lighting_demand,
        fastened_appliances_va=fastened_connected,
        fastened_demand_va=fastened_demand,
        range_connected_va=range_connected,
        range_demand_va=range_dem,
        dryer_connected_va=dryer_connected,
        dryer_demand_va=dryer_dem,
        hvac_va=hvac_va,
        motor_adder_va=motor_adder,
        total_va=total_va,
        total_amps=total_amps,
        neutral_va=neutral_va,
        neutral_amps=neutral_amps,
        recommended_service_amps=recommended,
        sufficient_existing=sufficient,
        breakdown={
            "general_lighting": gl,
            "small_appliance": small,
            "laundry": laundry,
            "lighting_load": lighting_load,
            "lighting_demand": lighting_demand,
            "fastened_connected": fastened_connected,
            "fastened_demand": fastened_demand,
            "range_connected": range_connected,
            "range_demand": range_dem,
            "dryer_connected": dryer_connected,
            "dryer_demand": dryer_dem,
            "hvac": hvac_va,
            "motor_adder": motor_adder,
            "total": total_va,
        },
        notes=notes,
    )


# ---------- Optional 220.82 (single dwelling) ----------

def optional_220_82(inp: ProjectInput) -> LoadResult:
    notes: list[str] = []
    gl = 3.0 * inp.floor_area_sqft
    small = 1500.0 * inp.small_appliance_circuits
    laundry = 1500.0 * inp.laundry_circuits
    fastened_connected, _, _ = _fastened(inp)
    rr = _range_ratings(inp)
    range_connected = sum(r * 1000.0 for r in rr)
    dv = _dryer_va_list(inp)
    dryer_connected = sum(dv)

    hvac = inp.hvac
    # 220.82(C) largest of six
    options = []
    if hvac.cooling_va > 0:
        options.append(hvac.cooling_va)  # (1)
    if hvac.heat_pump and hvac.supplemental_heat_va <= 0 and hvac.heating_va > 0:
        options.append(hvac.heating_va)  # (2)
    if hvac.heat_pump and hvac.supplemental_heat_va > 0:
        supp_factor = 0.65 if hvac.space_heating_units < 4 else 0.40
        options.append(hvac.cooling_va + hvac.supplemental_heat_va * supp_factor)  # (3)
    if not hvac.heat_pump and hvac.heating_va > 0:
        factor = 0.65 if hvac.space_heating_units < 4 else 0.40
        options.append(hvac.heating_va * factor)  # (4)(5)
    if hvac.thermal_storage and hvac.heating_va > 0:
        options.append(hvac.heating_va)  # (6)
    hvac_va = max(options) if options else 0.0

    general_items = gl + small + laundry + fastened_connected + range_connected + dryer_connected + inp.largest_motor_va
    if general_items <= 10000:
        general_demand = general_items
    else:
        general_demand = 10000 + 0.4 * (general_items - 10000)
    total_va = general_demand + hvac_va

    neutral_va = (gl + small + laundry + fastened_connected + inp.largest_motor_va) + (range_connected + dryer_connected) * 0.7

    total_amps = total_va / 240.0
    neutral_amps = neutral_va / 240.0
    recommended = recommend_service_amps(total_amps)

    notes.append("NEC 220.82 optional method (single dwelling).")

    return LoadResult(
        method="optional_220_82",
        general_lighting_va=gl,
        small_appliance_va=small,
        laundry_va=laundry,
        lighting_load_va=gl + small + laundry,
        lighting_demand_va=general_demand,
        fastened_appliances_va=fastened_connected,
        fastened_demand_va=fastened_connected,  # folded into general
        range_connected_va=range_connected,
        range_demand_va=range_connected,
        dryer_connected_va=dryer_connected,
        dryer_demand_va=dryer_connected,
        hvac_va=hvac_va,
        motor_adder_va=inp.largest_motor_va,
        total_va=total_va,
        total_amps=total_amps,
        neutral_va=neutral_va,
        neutral_amps=neutral_amps,
        recommended_service_amps=recommended,
        breakdown={
            "general_items": general_items,
            "general_demand": general_demand,
            "hvac": hvac_va,
            "total": total_va,
        },
        notes=notes,
    )


# ---------- Optional 220.83 (existing dwelling) ----------

def optional_220_83(inp: ProjectInput) -> LoadResult:
    notes: list[str] = []
    gl = 3.0 * inp.floor_area_sqft
    small = 1500.0 * inp.small_appliance_circuits
    laundry = 1500.0 * inp.laundry_circuits
    fastened_connected, _, _ = _fastened(inp)
    rr = _range_ratings(inp)
    range_connected = sum(r * 1000.0 for r in rr)
    dv = _dryer_va_list(inp)
    dryer_connected = sum(dv)
    hvac = inp.hvac

    has_new_hvac = (hvac.cooling_va > 0 or hvac.heating_va > 0) and (inp.existing_service_amps is not None)

    other_items = gl + small + laundry + fastened_connected + range_connected + dryer_connected + inp.largest_motor_va

    if has_new_hvac:
        # 220.83(B): HVAC at 100%, other loads first 8kVA 100% rest 40%
        cooling = hvac.cooling_va
        heating = hvac.heating_va
        hvac_va = max(cooling, heating)
        if other_items <= 8000:
            other_demand = other_items
        else:
            other_demand = 8000 + 0.4 * (other_items - 8000)
        total_va = other_demand + hvac_va
        notes.append("NEC 220.83(B): new HVAC installed; HVAC at 100%.")
    else:
        # 220.83(A): no new HVAC
        hvac_va = 0.0
        total_connected = other_items
        if total_connected <= 8000:
            total_va = total_connected
        else:
            total_va = 8000 + 0.4 * (total_connected - 8000)
        notes.append("NEC 220.83(A): no new HVAC.")

    neutral_va = other_items * 0.4 if other_items > 8000 else other_items  # rough
    # better: neutral = lighting+small+laundry+fastened + 0.7*(range+dryer), with reduction
    neutral_va = (gl + small + laundry + fastened_connected + inp.largest_motor_va) + (range_connected + dryer_connected) * 0.7

    total_amps = total_va / 240.0
    neutral_amps = neutral_va / 240.0
    recommended = recommend_service_amps(total_amps)

    sufficient = None
    if inp.existing_service_amps is not None:
        sufficient = total_amps <= inp.existing_service_amps

    return LoadResult(
        method="optional_220_83",
        general_lighting_va=gl,
        small_appliance_va=small,
        laundry_va=laundry,
        lighting_load_va=gl + small + laundry,
        lighting_demand_va=total_va,
        fastened_appliances_va=fastened_connected,
        fastened_demand_va=fastened_connected,
        range_connected_va=range_connected,
        range_demand_va=range_connected,
        dryer_connected_va=dryer_connected,
        dryer_demand_va=dryer_connected,
        hvac_va=hvac_va,
        motor_adder_va=inp.largest_motor_va,
        total_va=total_va,
        total_amps=total_amps,
        neutral_va=neutral_va,
        neutral_amps=neutral_amps,
        recommended_service_amps=recommended,
        sufficient_existing=sufficient,
        breakdown={"other_items": other_items, "total": total_va},
        notes=notes,
    )


# ---------- Optional 220.84 (multi-family) ----------

_MULTIFAMILY_FACTORS = [
    (3, 5, 0.45), (6, 7, 0.44), (8, 10, 0.43), (11, 11, 0.42),
    (12, 13, 0.41), (14, 15, 0.40), (16, 17, 0.39), (18, 20, 0.38),
    (21, 21, 0.37), (22, 23, 0.36), (24, 25, 0.35), (26, 27, 0.34),
    (28, 30, 0.33), (31, 31, 0.32), (32, 33, 0.31), (34, 36, 0.30),
    (37, 38, 0.29), (39, 42, 0.28), (43, 45, 0.27), (46, 50, 0.26),
    (51, 55, 0.25), (56, 61, 0.24),
]


def multifamily_demand_factor(n: int) -> float:
    if n < 3:
        return 1.0
    for lo, hi, f in _MULTIFAMILY_FACTORS:
        if lo <= n <= hi:
            return f
    return 0.23


def optional_220_84(inp: ProjectInput) -> LoadResult:
    notes: list[str] = []
    units = max(inp.num_units, 1)
    gl = 3.0 * inp.floor_area_sqft
    small = 1500.0 * inp.small_appliance_circuits
    laundry = 1500.0 * inp.laundry_circuits
    fastened_connected, _, _ = _fastened(inp)
    rr = _range_ratings(inp)
    range_connected = sum(r * 1000.0 for r in rr)
    dv = _dryer_va_list(inp)
    dryer_connected = sum(dv)
    hvac_va = max(inp.hvac.cooling_va, inp.hvac.heating_va)

    per_unit = gl + small + laundry + fastened_connected + range_connected + dryer_connected + inp.largest_motor_va + hvac_va
    total_connected = per_unit * units

    factor = multifamily_demand_factor(units)
    if units < 3:
        notes.append("NEC 220.84 requires 3+ units; using 100% demand factor.")
    total_va = total_connected * factor

    neutral_va = (gl + small + laundry + fastened_connected + inp.largest_motor_va + range_connected * 0.7 + dryer_connected * 0.7 + hvac_va * 0) * units
    # hvac excluded from neutral (240V)
    neutral_va = (gl + small + laundry + fastened_connected + inp.largest_motor_va + range_connected * 0.7 + dryer_connected * 0.7) * units * factor
    # keep neutral conservative: no demand reduction on neutral? Use factor too.

    total_amps = total_va / 240.0
    neutral_amps = neutral_va / 240.0
    recommended = recommend_service_amps(total_amps)

    notes.append(f"NEC 220.84: demand factor {factor*100:.0f}% for {units} units.")

    return LoadResult(
        method="optional_220_84",
        general_lighting_va=gl * units,
        small_appliance_va=small * units,
        laundry_va=laundry * units,
        lighting_load_va=(gl + small + laundry) * units,
        lighting_demand_va=total_va,
        fastened_appliances_va=fastened_connected * units,
        fastened_demand_va=fastened_connected * units * factor,
        range_connected_va=range_connected * units,
        range_demand_va=range_connected * units * factor,
        dryer_connected_va=dryer_connected * units,
        dryer_demand_va=dryer_connected * units * factor,
        hvac_va=hvac_va * units,
        motor_adder_va=inp.largest_motor_va * units,
        total_va=total_va,
        total_amps=total_amps,
        neutral_va=neutral_va,
        neutral_amps=neutral_amps,
        recommended_service_amps=recommended,
        breakdown={
            "per_unit_connected": per_unit,
            "total_connected": total_connected,
            "demand_factor": factor,
            "total": total_va,
        },
        notes=notes,
    )


def calculate_all(inp: ProjectInput) -> dict:
    """Run standard + applicable optional methods."""
    results = {"standard": standard_method(inp)}
    results["optional_220_82"] = optional_220_82(inp)
    results["optional_220_83"] = optional_220_83(inp)
    if inp.num_units >= 3:
        results["optional_220_84"] = optional_220_84(inp)
    return results

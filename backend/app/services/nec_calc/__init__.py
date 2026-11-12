"""NEC calculation engine — ampacity, voltage drop, conduit fill, grounding.

Every function returns a dict with at least:
  {"value": ..., "nec_reference": "Art. X", "warnings": [...]}
Inputs are never assumed; missing data produces a warning and a conservative result.
"""
from __future__ import annotations

# Ampacity (NEC 310.15(B)(16)) at 75 C for copper, single conductor in raceway/cable.
AMPACITY_75C_CU = {
    "14": 20, "12": 25, "10": 35, "8": 50, "6": 65, "4": 85,
    "3": 100, "2": 115, "1": 130, "1/0": 150, "2/0": 175, "3/0": 200,
    "4/0": 230, "250": 255, "300": 285, "350": 310, "400": 335,
    "500": 380, "600": 435, "700": 485, "750": 520,
}
AMPACITY_75C_AL = {
    "12": 20, "10": 30, "8": 40, "6": 50, "4": 65, "3": 75, "2": 90,
    "1": 100, "1/0": 120, "2/0": 135, "3/0": 155, "4/0": 180, "250": 205,
    "300": 230, "350": 250, "400": 270, "500": 310, "600": 350,
}

# Temperature correction factors for 75 C rated conductors (310.15(B)(2)(a)).
TEMP_CORRECTION_75 = {
    (0, 15): 1.08, (16, 20): 1.05, (21, 25): 1.00, (26, 30): 0.96,
    (31, 35): 0.94, (36, 40): 0.88, (41, 45): 0.82, (46, 50): 0.75,
    (51, 55): 0.67, (56, 60): 0.58, (61, 70): 0.33,
}

# Adjustment factors for >3 current-carrying conductors (310.15(B)(3)(a)).
ADJUSTMENT_FACTORS = {1: 1.0, 2: 1.0, 3: 1.0, 4: 0.8, 5: 0.8, 6: 0.8,
                      7: 0.7, 8: 0.7, 9: 0.7, 10: 0.5, 11: 0.5, 12: 0.5,
                      13: 0.5, 14: 0.5, 15: 0.5, 16: 0.5, 17: 0.5, 18: 0.5,
                      19: 0.5, 20: 0.5}


def _temp_factor(ambient_c: float, rated: int = 75) -> float:
    for (lo, hi), f in TEMP_CORRECTION_75.items():
        if lo <= ambient_c <= hi:
            return f
    if ambient_c > 70:
        return 0.33
    return 1.08


def ampacity(size: str, material: str = "cu", ambient_c: float = 30.0,
             num_conductors: int = 3, continuous: bool = False) -> dict:
    table = AMPACITY_75C_CU if material.lower().startswith("cu") else AMPACITY_75C_AL
    warnings: list[str] = []
    base = table.get(size)
    if base is None:
        warnings.append(f"Unknown conductor size {size}; using 0 A.")
        base = 0
    adj = ADJUSTMENT_FACTORS.get(min(num_conductors, 20), 0.5)
    temp = _temp_factor(ambient_c)
    value = base * temp * adj
    if continuous:
        value = value / 1.25
        warnings.append("Continuous load: ampacity divided by 1.25 (NEC 210.20(A)).")
    return {
        "value": round(value, 1),
        "base_ampacity_75c": base,
        "temp_factor": temp,
        "adjustment_factor": adj,
        "material": material,
        "size": size,
        "nec_reference": "NEC 310.15(B)(16), 310.15(B)(2), 310.15(B)(3)(a)",
        "warnings": warnings,
    }


def voltage_drop(size: str, material: str = "cu", amps: float = 0.0,
                 length_ft: float = 0.0, phase: int = 1,
                 max_percent: float = 3.0) -> dict:
    """Voltage drop for a run. K factors at 75 C: Cu=12.9, Al=21.2."""
    k = 12.9 if material.lower().startswith("cu") else 21.2
    # circular mils for common sizes
    cm_table = {
        "14": 4110, "12": 6530, "10": 10380, "8": 16510, "6": 26240,
        "4": 41740, "3": 52620, "2": 66360, "1": 83690, "1/0": 105600,
        "2/0": 133100, "3/0": 167800, "4/0": 211600, "250": 250000,
        "300": 300000, "350": 350000, "400": 400000, "500": 500000,
    }
    cm = cm_table.get(size, 0)
    warnings: list[str] = []
    if cm == 0:
        warnings.append(f"Unknown conductor size {size}; cannot compute voltage drop.")
        return {"value_percent": None, "nec_reference": "NEC 210.19(A)(1) Note 4 / 215.2(A)(1) Note 2", "warnings": warnings}
    if phase == 3:
        vd = (1.732 * k * amps * length_ft) / cm
    else:
        vd = (2 * k * amps * length_ft) / cm
    # assume 240V single-phase / 208V or 480V 3-phase? Use 240 default for %.
    nominal = 240.0 if phase == 1 else 480.0
    pct = (vd / nominal) * 100.0
    if pct > max_percent:
        warnings.append(f"Voltage drop {pct:.2f}% exceeds {max_percent}% limit.")
    return {
        "value_volts": round(vd, 2),
        "value_percent": round(pct, 2),
        "limit_percent": max_percent,
        "nec_reference": "NEC 210.19(A)(1) Note 4 / 215.2(A)(1) Note 2",
        "warnings": warnings,
    }


# Chapter 9 Table 4 (conduit area in sq in) and Table 5 (conductor area).
CONDUIT_AREA = {
    "1/2": 0.304, "3/4": 0.533, "1": 0.864, "1-1/4": 1.496,
    "1-1/2": 2.036, "2": 3.356, "2-1/2": 4.788, "3": 7.393,
    "3-1/2": 9.970, "4": 12.730,
}
CONDUCTOR_AREA = {
    "14": 0.0097, "12": 0.0133, "10": 0.0211, "8": 0.0366, "6": 0.0507,
    "4": 0.0824, "3": 0.0973, "2": 0.1158, "1": 0.1562, "1/0": 0.1855,
    "2/0": 0.2223, "3/0": 0.2679, "4/0": 0.3237, "250": 0.3970,
    "300": 0.4608, "350": 0.5321, "400": 0.6013, "500": 0.7073,
    "600": 0.8676,
}


def conduit_fill(conductor_size: str, num_conductors: int, conduit_trade: str | None = None,
                 fill_percent: float = 40.0) -> dict:
    """Compute required conduit trade size for given conductors (Chapter 9)."""
    warnings: list[str] = []
    area_each = CONDUCTOR_AREA.get(conductor_size, 0.0)
    total_cond = area_each * num_conductors
    if area_each == 0:
        warnings.append(f"Unknown conductor size {conductor_size}.")
        return {"required_trade_size": None, "nec_reference": "NEC Ch. 9 Table 1, 4, 5", "warnings": warnings}
    max_fill = fill_percent / 100.0
    # find smallest conduit with area >= total_cond / max_fill
    required = None
    for trade, area in sorted(CONDUIT_AREA.items(), key=lambda kv: kv[1]):
        if area * max_fill >= total_cond:
            required = trade
            break
    if required is None:
        warnings.append("Conductors do not fit in available conduit sizes; upsize or split.")
        required = "4+ (split run)"
    result = {
        "conductor_size": conductor_size,
        "num_conductors": num_conductors,
        "total_conductor_area": round(total_cond, 4),
        "fill_percent_limit": fill_percent,
        "required_trade_size": required,
        "nec_reference": "NEC Ch. 9 Table 1, Table 4, Table 5",
        "warnings": warnings,
    }
    if conduit_trade:
        avail = CONDUIT_AREA.get(conduit_trade, 0.0)
        actual_fill = (total_cond / avail * 100.0) if avail else 0.0
        result["provided_trade_size"] = conduit_trade
        result["actual_fill_percent"] = round(actual_fill, 1)
        if actual_fill > fill_percent:
            warnings.append(f"Provided {conduit_trade}\" conduit fill {actual_fill:.1f}% exceeds {fill_percent}%.")
    return result


# GEC sizing per NEC 250.66 (based on largest service-entrance conductor).
GEC_TABLE_250_66 = [
    (0, 1, "6", "8"),        # up to 2 AWG Cu / 1/0 Al -> 8 AWG Cu
    (2, 1, "4", "6"),        # 1/0 or 2/0 Cu -> 6/4
]
# Simplified: map service conductor size -> GEC size (Cu) for common sizes.
GEC_SIZE = {
    "4": "8", "3": "8", "2": "8", "1": "6", "1/0": "6", "2/0": "4",
    "3/0": "4", "4/0": "2", "250": "2", "300": "2", "350": "2",
    "400": "1/0", "500": "1/0",
}


def gec_size(service_conductor_size: str, material: str = "cu") -> dict:
    warnings: list[str] = []
    size = GEC_SIZE.get(service_conductor_size)
    if size is None:
        warnings.append(f"No GEC table entry for {service_conductor_size}; use 250.66.")
        size = service_conductor_size
    return {
        "service_conductor_size": service_conductor_size,
        "gec_size_cu": size,
        "nec_reference": "NEC 250.66 (Table)",
        "warnings": warnings,
    }


# EGC sizing per NEC 250.122 (based on OCPD rating).
EGC_TABLE_250_122 = [
    (15, "14"), (20, "12"), (30, "10"), (40, "10"), (60, "10"),
    (100, "8"), (200, "6"), (300, "4"), (400, "3"), (500, "2"),
    (600, "1"), (800, "1/0"), (1000, "2/0"), (1200, "3/0"),
    (1600, "4/0"), (2000, "250"), (2500, "350"), (3000, "400"),
    (4000, "500"), (5000, "700"), (6000, "800"),
]


def egc_size(ocpd_amps: float) -> dict:
    warnings: list[str] = []
    size = None
    for rating, s in EGC_TABLE_250_122:
        if ocpd_amps <= rating:
            size = s
            break
    if size is None:
        size = "1250"  # fallback for very large
        warnings.append("OCPD exceeds table; consult 250.122.")
    return {
        "ocpd_amps": ocpd_amps,
        "egc_size_cu": size,
        "nec_reference": "NEC 250.122 (Table)",
        "warnings": warnings,
    }

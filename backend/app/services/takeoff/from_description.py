"""Generate a takeoff from a free-text work description, using the NEC 2017
code text as a reference database for relevant articles."""
import re
from decimal import Decimal

from app.services.load_calc.engine import LoadCalcEngine
from app.services.load_calc.schemas import LoadCalcRequest
from app.services.takeoff.generator import generate_takeoff_from_calculation

# keyword -> (description, category, unit, unit_cost, labor_hours)
KEYWORD_ITEMS = {
    "receptacle": ("Duplex Receptacle", "device", "ea", Decimal("2.85"), 0.18),
    "outlet": ("Duplex Receptacle", "device", "ea", Decimal("2.85"), 0.18),
    "switch": ("Single-Pole Switch", "device", "ea", Decimal("2.40"), 0.2),
    "gfci": ("GFCI Receptacle", "device", "ea", Decimal("18.50"), 0.3),
    "afci": ("AFCI Breaker (20A)", "breaker", "ea", Decimal("42.00"), 0.125),
    "light": ("Lighting Fixture", "device", "ea", Decimal("35.00"), 0.5),
    "fan": ("Ceiling Fan", "device", "ea", Decimal("120.00"), 1.0),
    "smoke": ("Smoke Detector", "device", "ea", Decimal("25.00"), 0.4),
    "co detector": ("CO Detector", "device", "ea", Decimal("30.00"), 0.4),
}


def _nec_refs(description: str) -> list[str]:
    try:
        from app.routers.nec_reference import load_text
        text = load_text()
    except Exception:
        return []
    if not text:
        return []
    low = text.lower()
    refs = []
    # search for article/section numbers mentioned in description (e.g. 210.8, 220.12)
    for m in re.finditer(r"\b(\d{3}\.\d+(?:\([A-Za-z]\))?)\b", description):
        art = m.group(1)
        idx = low.find(art.lower())
        if idx != -1:
            s = max(0, idx - 80)
            e = min(len(text), idx + len(art) + 120)
            refs.append(text[s:e].replace("\n", " "))
    # keyword fallback
    if not refs:
        for kw in ("receptacle", "lighting", "service", "grounding"):
            if kw in description.lower():
                idx = low.find(kw)
                if idx != -1:
                    s = max(0, idx - 80)
                    e = min(len(text), idx + len(kw) + 120)
                    refs.append(text[s:e].replace("\n", " "))
                    break
    return refs[:5]


def generate_from_description(project, description: str) -> tuple[list, list[str]]:
    items = []
    desc_low = description.lower()

    # quantity extraction: "5 receptacles", "3 switches at $2"
    for kw, (d, cat, unit, cost, lh) in KEYWORD_ITEMS.items():
        # find patterns like "5 receptacles" or "receptacles x5"
        patterns = [
            rf"(\d+(?:\.\d+)?)\s+{re.escape(kw)}s?",
            rf"{re.escape(kw)}s?\s+x\s*(\d+(?:\.\d+)?)",
            rf"{re.escape(kw)}s?\s+(\d+(?:\.\d+)?)",
        ]
        qty = 0
        for pat in patterns:
            for m in re.finditer(pat, desc_low):
                try:
                    qty += float(m.group(1))
                except (ValueError, IndexError):
                    pass
        if qty <= 0 and kw in desc_low:
            qty = 1
        if qty > 0:
            items.append({
                "description": d,
                "category": cat,
                "quantity": qty,
                "unit": unit,
                "unit_cost": cost,
                "labor_hours": lh,
                "is_auto_generated": False,
                "notes": "From work description",
            })

    # if no specific items, fall back to full generator
    if not items:
        req = LoadCalcRequest(
            project_type=project.project_type if project.project_type in ("single_family", "multi_family", "adu", "duplex") else "single_family",
            floor_area_sqft=project.floor_area_sqft or 1500.0,
        )
        calc = LoadCalcEngine().calculate(req)[0]
        gen = generate_takeoff_from_calculation(project.id, calc, project.floor_area_sqft or 1500.0)
        for it in gen:
            items.append({
                "description": it.description,
                "category": it.category,
                "quantity": it.quantity,
                "unit": it.unit,
                "unit_cost": it.unit_cost,
                "labor_hours": it.labor_hours,
                "is_auto_generated": True,
                "notes": it.notes,
            })

    refs = _nec_refs(description)
    return items, refs

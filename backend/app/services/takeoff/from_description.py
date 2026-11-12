"""Generate a takeoff from a free-text work description, using the NEC 2017
code text as a reference database for relevant articles."""
import re
from decimal import Decimal

from app.services.load_calc.engine import LoadCalcEngine
from app.services.load_calc.schemas import LoadCalcRequest
from app.services.nec_calc import conduit_fill, voltage_drop
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
    refs: list[str] = []
    seen: set[int] = set()

    def add(needle: str) -> None:
        if not needle:
            return
        idx = low.find(needle.lower())
        while idx != -1 and len(refs) < 8:
            if all(abs(idx - p) > 60 for p in seen):
                seen.add(idx)
                s = max(0, idx - 80)
                e = min(len(text), idx + len(needle) + 160)
                refs.append(text[s:e].replace("\n", " "))
            idx = low.find(needle.lower(), idx + max(1, len(needle)))

    # article/section numbers mentioned explicitly in the description
    for m in re.finditer(r"\b(\d{3}\.\d+(?:\([A-Za-z]\))?)\b", description):
        add(m.group(1))

    dl = description.lower()
    service_job = any(k in dl for k in ("service", "panel", "meter", "mast", "overhead", "underground", "upgrade", "disconnect", "weatherhead"))

    if service_job:
        # Pull the governing NEC sections for a service upgrade out of the code book.
        for sec in ("230.24", "230.70", "230.79", "230.42", "250.50", "250.52", "250.53", "250.66", "310.15", "240.4", "220.83"):
            add(sec)
        for kw in ("service", "overhead", "clearance", "grounding electrode", "mast", "weatherhead", "disconnect", "conductor"):
            add(kw)
    else:
        for kw in ("receptacle", "lighting", "service", "grounding", "charger", "625"):
            if kw in dl:
                add(kw)
                break

    # keyword fallback when nothing matched
    if not refs:
        for kw in ("receptacle", "lighting", "service", "grounding", "charger", "625"):
            if kw in dl:
                add(kw)
                break

    return refs[:8]


def generate_from_description(project, description: str) -> tuple[list, list[str]]:
    items = []
    desc_low = description.lower()

    # EV charger / EVSE handling (e.g. "EV charger 110 feet from panel")
    ev_keywords = ["ev charger", "evse", "electric vehicle", "charger", "level 2", "tesla", "wall connector", "nema 14-50", "nema 6-50"]
    if any(k in desc_low for k in ev_keywords):
        dist = 0.0
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:feet|ft|')", desc_low)
        if m:
            dist = float(m.group(1))
        if dist <= 0:
            m2 = re.search(r"from\s+(?:the\s+)?panel\s+(\d+(?:\.\d+)?)", desc_low)
            if m2:
                dist = float(m2.group(1))
        if dist <= 0:
            m3 = re.search(r"(\d+(?:\.\d+)?)\s*(?:feet|ft)\s+from", desc_low)
            if m3:
                dist = float(m3.group(1))

        if "nema 14-50" in desc_low or "receptacle" in desc_low or "outlet" in desc_low or "plug" in desc_low:
            items.append({
                "description": "NEMA 14-50 Receptacle (EV)",
                "category": "device",
                "quantity": 1,
                "unit": "ea",
                "unit_cost": Decimal("45.00"),
                "labor_hours": Decimal("0.5"),
                "is_auto_generated": False,
                "notes": "EV charging receptacle",
            })
        else:
            items.append({
                "description": "EV Charger (Level 2, hardwired)",
                "category": "equipment",
                "quantity": 1,
                "unit": "ea",
                "unit_cost": Decimal("650.00"),
                "labor_hours": Decimal("2.0"),
                "is_auto_generated": False,
                "notes": "EVSE unit",
            })

        items.append({
            "description": "50A 2-Pole Breaker (EV)",
            "category": "breaker",
            "quantity": 1,
            "unit": "ea",
            "unit_cost": Decimal("22.00"),
            "labor_hours": Decimal("0.3"),
            "is_auto_generated": False,
            "notes": "EV branch circuit breaker",
        })

        if dist > 0:
            items.append({
                "description": "6 AWG THHN (EV circuit)",
                "category": "wire",
                "quantity": Decimal(str(round(dist * 3, 2))),
                "unit": "ft",
                "unit_cost": Decimal("0.75"),
                "labor_hours": Decimal("0.03"),
                "is_auto_generated": False,
                "notes": f"EV circuit conductors ({dist:.0f} ft run)",
            })
            items.append({
                "description": "3/4 in EMT Conduit (EV run)",
                "category": "conduit",
                "quantity": Decimal(str(dist)),
                "unit": "ft",
                "unit_cost": Decimal("0.65"),
                "labor_hours": Decimal("0.06"),
                "is_auto_generated": False,
                "notes": f"EV conduit run ({dist:.0f} ft)",
            })
            items.append({
                "description": "EMT Fittings & Straps (EV)",
                "category": "conduit",
                "quantity": 1,
                "unit": "lot",
                "unit_cost": Decimal("15.00"),
                "labor_hours": Decimal("0.5"),
                "is_auto_generated": False,
                "notes": "EV conduit fittings",
            })
            items.append({
                "description": "Wire Pull / Lubricant (EV)",
                "category": "wire",
                "quantity": 1,
                "unit": "lot",
                "unit_cost": Decimal("8.00"),
                "labor_hours": Decimal("0.3"),
                "is_auto_generated": False,
                "notes": "EV wire pull",
            })

        vd = voltage_drop("6", "cu", 50.0, dist if dist > 0 else 0.0, 1, 3.0) if dist > 0 else None
        if vd and vd.get("warnings"):
            items.append({
                "description": "Voltage Drop Check (EV circuit)",
                "category": "engineering",
                "quantity": 1,
                "unit": "ea",
                "unit_cost": Decimal("0.00"),
                "labor_hours": Decimal("0.0"),
                "is_auto_generated": False,
                "notes": "; ".join(vd["warnings"]) + f" (VD {vd.get('value_percent')}%)",
            })
        cf = conduit_fill("6", 3, "3/4", 40.0) if dist > 0 else None
        if cf and cf.get("warnings"):
            items.append({
                "description": "Conduit Fill Check (EV circuit)",
                "category": "engineering",
                "quantity": 1,
                "unit": "ea",
                "unit_cost": Decimal("0.00"),
                "labor_hours": Decimal("0.0"),
                "is_auto_generated": False,
                "notes": "; ".join(cf["warnings"]),
            })

        items.append({
            "description": "GFCI Protection (EV circuit)",
            "category": "safety",
            "quantity": 1,
            "unit": "ea",
            "unit_cost": Decimal("45.00"),
            "labor_hours": Decimal("0.2"),
            "is_auto_generated": False,
            "notes": "NEC 625.54 GFCI protection for EVSE",
        })

    # Service / panel upgrade handling (e.g. "upgrade panel 200A service overhead")
    service_keywords = ["panel", "service", "meter", "mast", "weatherhead", "overhead", "underground", "upgrade", "disconnect", "main breaker", "service entrance"]
    ev_job = any(k in desc_low for k in ev_keywords)
    service_job = (not ev_job) and any(k in desc_low for k in service_keywords) and ("panel" in desc_low or "service" in desc_low or "meter" in desc_low or "mast" in desc_low or "upgrade" in desc_low)
    if service_job:
        amps = 200
        m = re.search(r"(\d+)\s*a(?:mp)?(?:s)?\b", desc_low)
        if m:
            try:
                amps = int(m.group(1))
            except ValueError:
                amps = 200
        overhead = any(k in desc_low for k in ("overhead", "mast", "weatherhead", "pole", "aerial"))

        if amps <= 100:
            cond = "4 AWG Cu THWN (service entrance)"
            gec = "6 AWG Cu (GEC)"
        elif amps <= 200:
            cond = "2/0 Cu THWN (service entrance)"
            gec = "4 AWG Cu (GEC)"
        else:
            cond = "400 kcmil Cu (service entrance)"
            gec = "2 AWG Cu (GEC)"

        mast_len = 10 if overhead else 0
        run_len = 60 if overhead else 40

        items.append({
            "description": f"{amps}A Main Breaker Panel (load center)",
            "category": "panel",
            "quantity": 1,
            "unit": "ea",
            "unit_cost": Decimal("320.00" if amps <= 200 else "680.00"),
            "labor_hours": Decimal("4.0"),
            "is_auto_generated": False,
            "notes": f"NEC 230.79 / 408 - {amps}A service panel",
        })
        items.append({
            "description": f"{amps}A Meter Base (socket)",
            "category": "meter",
            "quantity": 1,
            "unit": "ea",
            "unit_cost": Decimal("185.00"),
            "labor_hours": Decimal("2.0"),
            "is_auto_generated": False,
            "notes": "Utility meter socket",
        })
        if overhead:
            items.append({
                "description": "Service Mast (2 in RMC/IMC)",
                "category": "conduit",
                "quantity": Decimal(str(mast_len)),
                "unit": "ft",
                "unit_cost": Decimal("12.50"),
                "labor_hours": Decimal("0.25"),
                "is_auto_generated": False,
                "notes": "NEC 230.24 clearance / mast height",
            })
            items.append({
                "description": "Weatherhead (service head)",
                "category": "fitting",
                "quantity": 1,
                "unit": "ea",
                "unit_cost": Decimal("28.00"),
                "labor_hours": Decimal("0.5"),
                "is_auto_generated": False,
                "notes": "Overhead service head",
            })
            items.append({
                "description": "Insulator / Drip Loop Hardware",
                "category": "fitting",
                "quantity": 1,
                "unit": "lot",
                "unit_cost": Decimal("25.00"),
                "labor_hours": Decimal("0.5"),
                "is_auto_generated": False,
                "notes": "Overhead service attachments",
            })
        else:
            items.append({
                "description": "2 in PVC Conduit (underground service)",
                "category": "conduit",
                "quantity": Decimal(str(run_len)),
                "unit": "ft",
                "unit_cost": Decimal("4.20"),
                "labor_hours": Decimal("0.15"),
                "is_auto_generated": False,
                "notes": "Underground service raceway",
            })
        items.append({
            "description": cond,
            "category": "wire",
            "quantity": Decimal(str(run_len * 3)),
            "unit": "ft",
            "unit_cost": Decimal("3.85"),
            "labor_hours": Decimal("0.05"),
            "is_auto_generated": False,
            "notes": f"Service entrance conductors ({run_len} ft run x3)",
        })
        vd_svc = voltage_drop(cond.split()[0] if False else "2/0", "cu", float(amps), float(run_len), 1, 3.0)
        if vd_svc.get("warnings"):
            items.append({
                "description": "Voltage Drop Check (service)",
                "category": "engineering",
                "quantity": 1,
                "unit": "ea",
                "unit_cost": Decimal("0.00"),
                "labor_hours": Decimal("0.0"),
                "is_auto_generated": False,
                "notes": "; ".join(vd_svc["warnings"]) + f" (VD {vd_svc.get('value_percent')}%)",
            })
        cf_svc = conduit_fill("2/0" if amps <= 200 else "4/0", 3, "2", 40.0)
        if cf_svc.get("warnings"):
            items.append({
                "description": "Conduit Fill Check (service)",
                "category": "engineering",
                "quantity": 1,
                "unit": "ea",
                "unit_cost": Decimal("0.00"),
                "labor_hours": Decimal("0.0"),
                "is_auto_generated": False,
                "notes": "; ".join(cf_svc["warnings"]),
            })

        items.append({
            "description": gec,
            "category": "wire",
            "quantity": Decimal(str(25)),
            "unit": "ft",
            "unit_cost": Decimal("1.60"),
            "labor_hours": Decimal("0.04"),
            "is_auto_generated": False,
            "notes": "NEC 250.66 GEC sizing",
        })
        items.append({
            "description": "Ground Rod 8 ft x 5/8 in (copper-clad)",
            "category": "grounding",
            "quantity": 2,
            "unit": "ea",
            "unit_cost": Decimal("18.00"),
            "labor_hours": Decimal("0.75"),
            "is_auto_generated": False,
            "notes": "NEC 250.52 / 250.53",
        })
        items.append({
            "description": "Ground Rod Clamp & Acorn Nut",
            "category": "grounding",
            "quantity": 2,
            "unit": "ea",
            "unit_cost": Decimal("6.50"),
            "labor_hours": Decimal("0.15"),
            "is_auto_generated": False,
            "notes": "Grounding electrode connection",
        })
        items.append({
            "description": "Main Bonding Jumper",
            "category": "grounding",
            "quantity": 1,
            "unit": "ea",
            "unit_cost": Decimal("12.00"),
            "labor_hours": Decimal("0.25"),
            "is_auto_generated": False,
            "notes": "NEC 250.28",
        })
        items.append({
            "description": "Neutral/Ground Bar Kit",
            "category": "panel",
            "quantity": 1,
            "unit": "ea",
            "unit_cost": Decimal("18.00"),
            "labor_hours": Decimal("0.25"),
            "is_auto_generated": False,
            "notes": "Panel accessory",
        })
        items.append({
            "description": "20A Single-Pole Breaker",
            "category": "breaker",
            "quantity": 10,
            "unit": "ea",
            "unit_cost": Decimal("8.50"),
            "labor_hours": Decimal("0.125"),
            "is_auto_generated": False,
            "notes": "Branch circuit breakers",
        })
        items.append({
            "description": "Permit / Inspection (service upgrade)",
            "category": "labor",
            "quantity": 1,
            "unit": "lot",
            "unit_cost": Decimal("250.00"),
            "labor_hours": Decimal("2.0"),
            "is_auto_generated": False,
            "notes": "AHJ permit & inspection",
        })

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

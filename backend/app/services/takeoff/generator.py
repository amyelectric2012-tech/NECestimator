from decimal import Decimal
from uuid import UUID

from app.schemas.takeoff import TakeoffItemCreate
from app.services.load_calc.schemas import LoadCalcResult


def generate_takeoff_from_calculation(
    project_id: UUID,
    calc_result: LoadCalcResult,
    floor_area_sqft: float,
) -> list[TakeoffItemCreate]:
    items: list[TakeoffItemCreate] = []
    service_amps = calc_result.recommended_service_amps

    items.append(TakeoffItemCreate(
        description=f"{service_amps}A Meter-Main Combination",
        category="service",
        quantity=1,
        unit="ea",
        unit_cost=Decimal("1450.00"),
        labor_hours=6.0,
        is_auto_generated=True,
        notes="Service equipment based on calculated load",
    ))

    items.append(TakeoffItemCreate(
        description=f"{service_amps}A Main Breaker Panel (40 circuit)",
        category="service",
        quantity=1,
        unit="ea",
        unit_cost=Decimal("780.00"),
        labor_hours=4.5,
        is_auto_generated=True,
    ))

    items.append(TakeoffItemCreate(
        description="Grounding Electrode System (rods + wire + clamps)",
        category="grounding",
        quantity=1,
        unit="lot",
        unit_cost=Decimal("185.00"),
        labor_hours=2.5,
        is_auto_generated=True,
    ))

    items.append(TakeoffItemCreate(
        description=f"Service Entrance Conductors (for {service_amps}A)",
        category="wire",
        quantity=40,
        unit="ft",
        unit_cost=Decimal("8.50"),
        labor_hours=0.075,
        is_auto_generated=True,
    ))

    estimated_devices = max(int(floor_area_sqft / 45), 20)

    items.append(TakeoffItemCreate(
        description="12/2 NM-B Cable (general lighting & receptacles)",
        category="wire",
        quantity=round(floor_area_sqft * 1.1, 0),
        unit="ft",
        unit_cost=Decimal("0.68"),
        labor_hours=round((floor_area_sqft / 120.0) / max(round(floor_area_sqft * 1.1, 0), 1), 4),
        is_auto_generated=True,
    ))

    items.append(TakeoffItemCreate(
        description="14/2 NM-B Cable (lighting)",
        category="wire",
        quantity=round(floor_area_sqft * 0.4, 0),
        unit="ft",
        unit_cost=Decimal("0.48"),
        labor_hours=round((floor_area_sqft / 200.0) / max(round(floor_area_sqft * 0.4, 0), 1), 4),
        is_auto_generated=True,
    ))

    items.append(TakeoffItemCreate(
        description="Duplex Receptacles",
        category="device",
        quantity=estimated_devices,
        unit="ea",
        unit_cost=Decimal("2.85"),
        labor_hours=0.18,
        is_auto_generated=True,
    ))

    items.append(TakeoffItemCreate(
        description="Switches (single-pole)",
        category="device",
        quantity=max(int(estimated_devices * 0.4), 8),
        unit="ea",
        unit_cost=Decimal("2.40"),
        labor_hours=0.2,
        is_auto_generated=True,
    ))

    items.append(TakeoffItemCreate(
        description="GFCI Receptacles",
        category="device",
        quantity=6,
        unit="ea",
        unit_cost=Decimal("18.50"),
        labor_hours=0.3,
        is_auto_generated=True,
    ))

    items.append(TakeoffItemCreate(
        description="AFCI Breakers (20A)",
        category="breaker",
        quantity=12,
        unit="ea",
        unit_cost=Decimal("42.00"),
        labor_hours=0.125,
        is_auto_generated=True,
    ))

    items.append(TakeoffItemCreate(
        description="Plastic Old-Work / New-Work Boxes",
        category="box",
        quantity=estimated_devices + 15,
        unit="ea",
        unit_cost=Decimal("1.15"),
        labor_hours=0.12,
        is_auto_generated=True,
    ))

    # ----- Conduit (service entrance + branch circuits) -----
    if service_amps >= 200:
        conduit_size = "2 in"
    elif service_amps >= 100:
        conduit_size = "1-1/4 in"
    else:
        conduit_size = "1 in"

    items.append(TakeoffItemCreate(
        description=f"{conduit_size} EMT Conduit - Service Entrance",
        category="conduit",
        quantity=40,
        unit="ft",
        unit_cost=Decimal("2.40"),
        labor_hours=round(40 / 40.0, 2),
        is_auto_generated=True,
        notes="Service entrance conduit run",
    ))

    items.append(TakeoffItemCreate(
        description="EMT Fittings & Straps (service)",
        category="conduit",
        quantity=1,
        unit="lot",
        unit_cost=Decimal("45.00"),
        labor_hours=1.0,
        is_auto_generated=True,
    ))

    branch_conduit_ft = round(floor_area_sqft / 2.0, 0)
    items.append(TakeoffItemCreate(
        description="1/2 in EMT Conduit - Branch Circuits",
        category="conduit",
        quantity=branch_conduit_ft,
        unit="ft",
        unit_cost=Decimal("0.95"),
        labor_hours=round(branch_conduit_ft / 60.0, 2),
        is_auto_generated=True,
        notes="Branch circuit conduit (rough estimate)",
    ))

    items.append(TakeoffItemCreate(
        description="Wire Pull / Pulling Lubricant",
        category="wire",
        quantity=1,
        unit="lot",
        unit_cost=Decimal("25.00"),
        labor_hours=0.5,
        is_auto_generated=True,
    ))

    return items

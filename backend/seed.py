import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine
from app.models import LaborRate, Material

Base.metadata.create_all(bind=engine)

MATERIALS = [
    ("P-100", "100A Main Panel", "panels", "ea", 180.0, 6.0, "service"),
    ("P-200", "200A Main Panel", "panels", "ea", 320.0, 8.0, "service"),
    ("CB-20", "20A Single Pole Breaker", "breakers", "ea", 8.0, 0.25, "trim"),
    ("CB-15", "15A Single Pole Breaker", "breakers", "ea", 7.0, 0.25, "trim"),
    ("CB-30", "30A Double Pole Breaker", "breakers", "ea", 14.0, 0.3, "trim"),
    ("CB-50", "50A Double Pole Breaker", "breakers", "ea", 22.0, 0.3, "trim"),
    ("CB-MAIN-100", "100A Main Breaker", "breakers", "ea", 45.0, 0.5, "service"),
    ("CB-MAIN-200", "200A Main Breaker", "breakers", "ea", 85.0, 0.5, "service"),
    ("W-14-2", "14/2 NM-B Romex", "wire", "ft", 0.35, 0.02, "rough_in"),
    ("W-12-2", "12/2 NM-B Romex", "wire", "ft", 0.45, 0.02, "rough_in"),
    ("W-10-2", "10/2 NM-B Romex", "wire", "ft", 0.75, 0.025, "rough_in"),
    ("W-12-3", "12/3 NM-B Romex", "wire", "ft", 0.6, 0.025, "rough_in"),
    ("W-SER-2", "2 AWG SER Feeder", "wire", "ft", 2.5, 0.05, "service"),
    ("W-SER-2-0", "2/0 AWG SER Feeder", "wire", "ft", 4.5, 0.06, "service"),
    ("B-DEVICE", "Device Box (single gang)", "boxes", "ea", 1.0, 0.15, "rough_in"),
    ("B-2GANG", "2-Gang Device Box", "boxes", "ea", 1.6, 0.2, "rough_in"),
    ("B-JB", "Junction Box 4x4", "boxes", "ea", 2.5, 0.2, "rough_in"),
    ("R-DUPLEX", "Duplex Receptacle 15A", "devices", "ea", 1.5, 0.25, "trim"),
    ("R-GFCI", "GFCI Receptacle 20A", "devices", "ea", 18.0, 0.35, "trim"),
    ("R-USB", "USB Receptacle", "devices", "ea", 22.0, 0.3, "trim"),
    ("S-SP", "Single Pole Switch", "devices", "ea", 1.2, 0.2, "trim"),
    ("S-3WAY", "3-Way Switch", "devices", "ea", 2.5, 0.25, "trim"),
    ("S-DIMMER", "Dimmer Switch", "devices", "ea", 18.0, 0.3, "trim"),
    ("F-RECESSED", "LED Recessed Light 6in", "fixtures", "ea", 25.0, 0.5, "trim"),
    ("F-FLUSH", "LED Flush Mount", "fixtures", "ea", 45.0, 0.6, "trim"),
    ("F-EXTERIOR", "Exterior Light Fixture", "fixtures", "ea", 35.0, 0.5, "trim"),
    ("SMOKE", "Smoke Detector Hardwired", "safety", "ea", 22.0, 0.3, "trim"),
    ("CO", "CO Detector", "safety", "ea", 35.0, 0.3, "trim"),
    ("GFCI-BREAKER", "GFCI Breaker 20A", "breakers", "ea", 45.0, 0.3, "trim"),
    ("AFI-BREAKER", "AFCI Breaker 15A", "breakers", "ea", 42.0, 0.3, "trim"),
    # Conduit & fittings
    ("C-EMT-1/2", "1/2 in EMT Conduit", "conduit", "ft", 0.45, 0.05, "rough_in"),
    ("C-EMT-3/4", "3/4 in EMT Conduit", "conduit", "ft", 0.65, 0.06, "rough_in"),
    ("C-EMT-1", "1 in EMT Conduit", "conduit", "ft", 1.1, 0.08, "rough_in"),
    ("C-EMT-1-1/4", "1-1/4 in EMT Conduit", "conduit", "ft", 1.6, 0.1, "rough_in"),
    ("C-PVC-1/2", "1/2 in PVC Conduit", "conduit", "ft", 0.35, 0.05, "rough_in"),
    ("C-PVC-3/4", "3/4 in PVC Conduit", "conduit", "ft", 0.5, 0.06, "rough_in"),
    ("FIT-EMT-1/2", "1/2 in EMT Connector", "fittings", "ea", 0.85, 0.05, "rough_in"),
    ("FIT-EMT-3/4", "3/4 in EMT Connector", "fittings", "ea", 1.1, 0.05, "rough_in"),
    ("STRAP-1/2", "1/2 in Conduit Strap", "fittings", "ea", 0.15, 0.02, "rough_in"),
    ("STRAP-3/4", "3/4 in Conduit Strap", "fittings", "ea", 0.2, 0.02, "rough_in"),
    # Wire & cable
    ("W-6-2", "6/2 NM-B Romex", "wire", "ft", 1.8, 0.04, "rough_in"),
    ("W-8-2", "8/2 NM-B Romex", "wire", "ft", 1.2, 0.03, "rough_in"),
    ("W-10-3", "10/3 NM-B Romex", "wire", "ft", 1.1, 0.03, "rough_in"),
    ("W-THHN-12", "12 AWG THHN", "wire", "ft", 0.25, 0.02, "rough_in"),
    ("W-THHN-10", "10 AWG THHN", "wire", "ft", 0.4, 0.025, "rough_in"),
    ("W-THHN-8", "8 AWG THHN", "wire", "ft", 0.75, 0.03, "rough_in"),
    ("W-GND-8", "8 AWG Bare Ground", "wire", "ft", 0.5, 0.02, "rough_in"),
    # Boxes & covers
    ("B-4S", "4-Square Box 1-1/2", "boxes", "ea", 2.0, 0.15, "rough_in"),
    ("B-4S-2G", "4-Square Box 2-Gang", "boxes", "ea", 3.0, 0.2, "rough_in"),
    ("COVER-SS", "Stainless Steel Cover Plate", "trim", "ea", 1.5, 0.1, "trim"),
    ("COVER-PLASTIC", "Plastic Cover Plate", "trim", "ea", 0.4, 0.05, "trim"),
    # Devices
    ("R-20A", "Duplex Receptacle 20A", "devices", "ea", 2.0, 0.25, "trim"),
    ("R-TAMPER", "Tamper-Resistant Receptacle", "devices", "ea", 2.5, 0.25, "trim"),
    ("R-WEATHER", "Weather-Resistant Receptacle", "devices", "ea", 3.5, 0.3, "trim"),
    ("S-TIMER", "Timer Switch", "devices", "ea", 25.0, 0.3, "trim"),
    ("S-MOTION", "Motion Sensor Switch", "devices", "ea", 30.0, 0.3, "trim"),
    # Fixtures
    ("F-PENDANT", "Pendant Light", "fixtures", "ea", 55.0, 0.6, "trim"),
    ("F-CEILING-FAN", "Ceiling Fan with Light", "fixtures", "ea", 120.0, 1.0, "trim"),
    ("F-EMERGENCY", "Emergency Light", "fixtures", "ea", 40.0, 0.5, "trim"),
    ("F-EXIT", "Exit Sign", "fixtures", "ea", 30.0, 0.4, "trim"),
    # Safety
    ("SMOKE-CO", "Combo Smoke/CO Detector", "safety", "ea", 45.0, 0.35, "trim"),
    ("GFCI-OUTLET-EXT", "Exterior GFCI Outlet", "devices", "ea", 20.0, 0.35, "trim"),
    # Service
    ("METER-SOCKET", "Meter Socket 200A", "service", "ea", 120.0, 2.0, "service"),
    ("GROUND-ROD", "Ground Rod 8ft", "grounding", "ea", 12.0, 0.5, "service"),
    ("GROUND-CLAMP", "Ground Clamp", "grounding", "ea", 3.0, 0.1, "service"),
    ("BOND-WIRE", "Bonding Wire #6", "grounding", "ft", 0.6, 0.03, "service"),
    ("PANEL-40CCT", "40-Circuit Panel", "panels", "ea", 200.0, 4.0, "service"),
    ("PANEL-30CCT", "30-Circuit Panel", "panels", "ea", 150.0, 3.5, "service"),
    # Misc
    ("WIRE-NUT-YELLOW", "Wire Nut Yellow", "misc", "ea", 0.1, 0.01, "rough_in"),
    ("WIRE-NUT-RED", "Wire Nut Red", "misc", "ea", 0.12, 0.01, "rough_in"),
    ("TAPE-ELEC", "Electrical Tape", "misc", "ea", 1.5, 0.01, "rough_in"),
    ("CAULK", "Fire Caulk Tube", "misc", "ea", 8.0, 0.1, "rough_in"),
    ("ANCHOR-CONC", "Concrete Anchor", "misc", "ea", 0.5, 0.05, "rough_in"),
]

LABOR_RATES = [
    ("rough_in", 45.0, "Rough-in labor"),
    ("trim", 50.0, "Trim/finish labor"),
    ("service", 65.0, "Service labor"),
    ("general", 48.0, "General labor"),
]


def seed():
    db = SessionLocal()
    try:
        for sku, name, cat, unit, cost, hours, lcat in MATERIALS:
            if db.query(Material).filter(Material.sku == sku).first():
                continue
            db.add(Material(sku=sku, name=name, category=cat, unit=unit, unit_cost=cost, labor_hours=hours, labor_category=lcat))
        for cat, rate, desc in LABOR_RATES:
            if db.query(LaborRate).filter(LaborRate.category == cat).first():
                continue
            db.add(LaborRate(category=cat, hourly_rate=rate, description=desc))
        db.commit()
        print("Seeded materials and labor rates.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

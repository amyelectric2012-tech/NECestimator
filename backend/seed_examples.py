import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from app.auth.jwt import get_password_hash
from app.database import Base, SessionLocal, engine
from app.models import Project, User

Base.metadata.create_all(bind=engine)

EXAMPLES = [
    {
        "name": "1500 sqft Single-Family (basic)",
        "project_type": "single_family",
        "floor_area_sqft": 1500,
        "num_units": 1,
        "small_appliance_circuits": 2,
        "laundry_circuits": 1,
        "appliances": [
            {"name": "water_heater", "va": 4500, "fastened": True},
            {"name": "dishwasher", "va": 1200, "fastened": True},
            {"name": "disposal", "va": 800, "fastened": True},
        ],
        "range_count": 1, "range_kw_each": 8.0,
        "dryer_count": 1, "dryer_kw_each": 5.0,
        "hvac": {"cooling_va": 3000, "heating_va": 0},
        "largest_motor_va": 3000,
    },
    {
        "name": "2400 sqft Single-Family (full appliances)",
        "project_type": "single_family",
        "floor_area_sqft": 2400,
        "num_units": 1,
        "small_appliance_circuits": 2,
        "laundry_circuits": 1,
        "appliances": [
            {"name": "water_heater", "va": 4500, "fastened": True},
            {"name": "dishwasher", "va": 1200, "fastened": True},
            {"name": "disposal", "va": 900, "fastened": True},
            {"name": "microwave", "va": 1500, "fastened": True},
            {"name": "refrigerator", "va": 800, "fastened": True},
        ],
        "range_count": 1, "range_kw_each": 12.0,
        "dryer_count": 1, "dryer_kw_each": 5.5,
        "hvac": {"cooling_va": 5000, "heating_va": 0},
        "largest_motor_va": 4000,
    },
    {
        "name": "4-Unit Multi-Family (220.84)",
        "project_type": "multi_family",
        "floor_area_sqft": 900,
        "num_units": 4,
        "small_appliance_circuits": 2,
        "laundry_circuits": 1,
        "appliances": [
            {"name": "water_heater", "va": 4500, "fastened": True},
            {"name": "dishwasher", "va": 1200, "fastened": True},
        ],
        "range_count": 1, "range_kw_each": 8.0,
        "dryer_count": 1, "dryer_kw_each": 5.0,
        "hvac": {"cooling_va": 3000, "heating_va": 0},
        "largest_motor_va": 2000,
    },
]


def seed_examples():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@example.com").first()
        if not user:
            user = User(email="demo@example.com", hashed_password=get_password_hash("demo123"), full_name="Demo User")
            db.add(user)
            db.commit()
            db.refresh(user)
        for ex in EXAMPLES:
            if db.query(Project).filter(Project.owner_id == user.id, Project.name == ex["name"]).first():
                continue
            p = Project(owner_id=user.id, **ex)
            db.add(p)
        db.commit()
        print(f"Seeded {len(EXAMPLES)} example projects for demo@example.com (password: demo123)")
    finally:
        db.close()


if __name__ == "__main__":
    seed_examples()

import sys

sys.path.insert(0, ".")

from app.services.load_calc.engine import LoadCalcEngine
from app.services.load_calc.schemas import ApplianceInput, LoadCalcRequest


def test_engine_single_family_both_methods():
    req = LoadCalcRequest(
        project_type="single_family",
        floor_area_sqft=2400,
        appliances=[
            ApplianceInput(name="Range", rating_kw=12.0),
            ApplianceInput(name="Dryer", rating_kw=5.5),
            ApplianceInput(name="Water Heater", rating_kw=4.5, is_fastened=True),
        ],
        hvac_cooling_va=6000,
        include_both_methods=True,
    )
    res = LoadCalcEngine().calculate(req)
    assert len(res) == 3
    assert res[0].method == "standard"
    assert res[1].method == "optional_220_82"
    assert res[2].method == "optional_220_83"
    assert res[0].total_demand_va > 0
    assert res[1].total_demand_va > 0


def test_engine_multi_family():
    req = LoadCalcRequest(
        project_type="multi_family",
        floor_area_sqft=900,
        num_units=4,
        appliances=[
            ApplianceInput(name="Range", rating_kw=8.0),
            ApplianceInput(name="Water Heater", rating_kw=4.5, is_fastened=True),
        ],
        hvac_cooling_va=3000,
        include_both_methods=True,
    )
    res = LoadCalcEngine().calculate(req)
    assert len(res) == 2
    assert res[0].method == "standard"
    assert res[1].method == "optional_220_84"


def test_engine_no_optional():
    req = LoadCalcRequest(
        project_type="single_family",
        floor_area_sqft=1500,
        include_both_methods=False,
    )
    res = LoadCalcEngine().calculate(req)
    assert len(res) == 1
    assert res[0].method == "standard"


def test_engine_endpoint():
    import os
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base, get_db
    from app.main import app
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    Base.metadata.create_all(bind=eng)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    client.post("/auth/register", json={"email": "calc@test.com", "password": "pw123"})
    r = client.post("/auth/login", json={"email": "calc@test.com", "password": "pw123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    payload = {
        "project_type": "single_family",
        "floor_area_sqft": 1500,
        "appliances": [{"name": "Range", "rating_kw": 8.0}],
        "hvac_cooling_va": 3000,
        "include_both_methods": True,
    }
    r = client.post("/calculations", json=payload, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["method"] == "standard"
    app.dependency_overrides.clear()

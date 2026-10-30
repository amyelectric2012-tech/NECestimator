import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_register_login():
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "pw123"})
    assert r.status_code == 200
    r = client.post("/auth/login", json={"email": "a@b.com", "password": "pw123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_project_calculate_takeoff_pdf():
    r = client.post("/auth/login", json={"email": "a@b.com", "password": "pw123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    # create
    r = client.post("/projects", json={"name": "T", "project_type": "single_family", "floor_area_sqft": 1500, "num_units": 1, "appliances": [{"name": "wh", "va": 4500, "fastened": True}], "range_count": 1, "range_kw_each": 8, "dryer_count": 1, "dryer_kw_each": 5, "hvac": {"cooling_va": 3000}, "largest_motor_va": 3000}, headers=h)
    assert r.status_code == 200
    pid = r.json()["id"]
    # calculate
    r = client.post(f"/projects/{pid}/calculate", headers=h)
    assert r.status_code == 200
    assert "standard" in r.json()["results"]
    # takeoff
    r = client.post(f"/projects/{pid}/takeoff", headers=h)
    assert r.status_code == 200
    eid = r.json()["id"]
    # pdf
    r = client.get(f"/projects/{pid}/export-pdf?estimate_id={eid}", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    # nec search
    r = client.get("/nec/search?q=220.42", headers=h)
    assert r.status_code == 200

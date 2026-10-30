import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _token():
    client.post("/auth/register", json={"email": "t@t.com", "password": "pw123"})
    r = client.post("/auth/login", json={"email": "t@t.com", "password": "pw123"})
    return r.json()["access_token"]


def _project(token):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/projects", json={"name": "T", "project_type": "single_family", "floor_area_sqft": 1800}, headers=h)
    return r.json()["id"], h


def test_takeoff_requires_auth():
    r = client.get("/projects/00000000-0000-0000-0000-000000000000/takeoff-items/")
    assert r.status_code in (401, 403)


def test_takeoff_generate_and_summary():
    token = _token()
    pid, h = _project(token)
    r = client.post(f"/projects/{pid}/takeoff-items/generate?floor_area_sqft=1800", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 10
    r = client.get(f"/projects/{pid}/takeoff-items/", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert "total_material_cost" in d
    assert float(d["grand_total"]) > 0


def test_takeoff_add_patch_delete():
    token = _token()
    pid, h = _project(token)
    # add
    r = client.post(f"/projects/{pid}/takeoff-items/", json={
        "description": "Test item", "category": "misc", "quantity": 2, "unit": "ea",
        "unit_cost": "10.00", "labor_hours": 0.5
    }, headers=h)
    assert r.status_code == 200
    item_id = r.json()["id"]
    # patch
    r = client.patch(f"/projects/{pid}/takeoff-items/{item_id}", json={"quantity": 5}, headers=h)
    assert r.status_code == 200
    assert r.json()["quantity"] == 5
    # delete
    r = client.delete(f"/projects/{pid}/takeoff-items/{item_id}", headers=h)
    assert r.status_code == 200


def test_takeoff_404_project():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/projects/00000000-0000-0000-0000-000000000000/takeoff-items/", headers=h)
    assert r.status_code == 404

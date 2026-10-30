from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Estimate, Material, Project
from app.schemas.schemas import EstimateCreate, EstimateOut, EstimateUpdate

router = APIRouter(prefix="/projects", tags=["estimates"])


def _calc_totals(est: Estimate, materials_by_id: dict):
    total_mat = 0.0
    total_hours = 0.0
    for li in (est.line_items or []):
        qty = li.get("qty", 0) or 0
        uc = li.get("unit_cost", 0) or 0
        lh = li.get("labor_hours", 0) or 0
        li["line_total"] = round(qty * uc, 2)
        li["line_labor"] = round(qty * lh, 2)
        total_mat += qty * uc
        total_hours += qty * lh
    mat_with_markup = total_mat * (1 + (est.markup_pct or 0)) * (1 + (est.tax_pct or 0))
    est.total_materials = round(total_mat, 2)
    est.total_labor_hours = round(total_hours, 2)
    est.total_cost = round(mat_with_markup, 2)


@router.post("/{project_id}/estimates", response_model=EstimateOut)
def create_estimate(project_id: str, payload: EstimateCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    est = Estimate(project_id=proj.id, **payload.model_dump())
    _calc_totals(est, {})
    db.add(est)
    db.commit()
    db.refresh(est)
    return est


@router.get("/{project_id}/estimates", response_model=list[EstimateOut])
def list_estimates(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Estimate).filter(Estimate.project_id == proj.id).order_by(Estimate.created_at.desc()).all()


@router.get("/{project_id}/estimates/{estimate_id}", response_model=EstimateOut)
def get_estimate(project_id: str, estimate_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    est = db.query(Estimate).filter(Estimate.id == estimate_id, Estimate.project_id == proj.id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return est


@router.put("/{project_id}/estimates/{estimate_id}", response_model=EstimateOut)
def update_estimate(project_id: str, estimate_id: str, payload: EstimateUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    est = db.query(Estimate).filter(Estimate.id == estimate_id, Estimate.project_id == proj.id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(est, k, v)
    _calc_totals(est, {})
    db.commit()
    db.refresh(est)
    return est


@router.delete("/{project_id}/estimates/{estimate_id}")
def delete_estimate(project_id: str, estimate_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    est = db.query(Estimate).filter(Estimate.id == estimate_id, Estimate.project_id == proj.id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    db.delete(est)
    db.commit()
    return {"deleted": True}


@router.post("/{project_id}/takeoff")
def generate_takeoff(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    # get latest standard load calc
    from app.models import LoadCalculation
    lc = db.query(LoadCalculation).filter(LoadCalculation.project_id == proj.id, LoadCalculation.method == "standard").order_by(LoadCalculation.created_at.desc()).first()
    if not lc:
        # run calculation
        pass
    results = lc.results if lc else None
    if results is None:
        from app.calculations.nec220 import standard_method
        from app.routers.projects import _to_input
        inp = _to_input(proj)
        r = standard_method(inp)
        results = r.__dict__ if hasattr(r, "__dict__") else {}
        # use breakdown
    res = results.get("breakdown", results) if isinstance(results, dict) else {}
    total_va = res.get("total", 0) if isinstance(res, dict) else 0
    amps = total_va / 240.0 if total_va else 0

    # material catalog lookup
    {m.name.lower(): m for m in db.query(Material).all()}
    def find(name_substr):
        for m in db.query(Material).all():
            if name_substr.lower() in m.name.lower():
                return m
        return None

    line_items = []
    def add(name_substr, qty, fallback_name=None, unit="ea", unit_cost=0.0, labor_hours=0.0, labor_category="rough_in"):
        m = find(name_substr)
        if m:
            line_items.append({"material_id": m.id, "name": m.name, "qty": qty, "unit": m.unit,
                               "unit_cost": m.unit_cost, "labor_hours": m.labor_hours,
                               "labor_category": m.labor_category})
        else:
            line_items.append({"material_id": None, "name": fallback_name or name_substr, "qty": qty, "unit": unit,
                               "unit_cost": unit_cost, "labor_hours": labor_hours, "labor_category": labor_category})

    # service panel based on recommended amps
    from app.calculations.nec220 import recommend_service_amps
    rec = recommend_service_amps(amps)
    add("panel", 1, fallback_name=f"{rec}A Main Panel", unit_cost=350.0, labor_hours=8.0, labor_category="service")

    # main breaker
    add("breaker", 1, fallback_name=f"{rec}A Main Breaker", unit_cost=45.0, labor_hours=0.5, labor_category="service")

    # feeder wire (rough: 1 set)
    if amps > 100:
        add("wire", 50, fallback_name="2/0 AWG SER (feeder)", unit="ft", unit_cost=4.5, labor_hours=0.05, labor_category="service")
    else:
        add("wire", 50, fallback_name="2 AWG SER (feeder)", unit="ft", unit_cost=2.5, labor_hours=0.05, labor_category="service")

    # branch circuits estimate: 1 circuit per 600 sqft? heuristic
    circuits = max(6, int(proj.floor_area_sqft / 150) + 4)
    add("romex", circuits * 75, fallback_name="12/2 NM-B", unit="ft", unit_cost=0.45, labor_hours=0.02, labor_category="rough_in")
    add("breaker", circuits, fallback_name="20A Breaker", unit_cost=8.0, labor_hours=0.25, labor_category="trim")

    # devices: receptacles/outlets heuristic
    outlets = max(8, int(proj.floor_area_sqft / 80))
    add("receptacle", outlets, fallback_name="Duplex Receptacle", unit_cost=1.5, labor_hours=0.25, labor_category="trim")
    switches = max(4, int(proj.floor_area_sqft / 200))
    add("switch", switches, fallback_name="Single Pole Switch", unit_cost=1.2, labor_hours=0.2, labor_category="trim")
    boxes = outlets + switches + circuits
    add("box", boxes, fallback_name="Device Box", unit_cost=1.0, labor_hours=0.15, labor_category="rough_in")

    # lighting fixtures placeholder
    fixtures = max(6, int(proj.floor_area_sqft / 120))
    add("fixture", fixtures, fallback_name="LED Recessed Light", unit_cost=25.0, labor_hours=0.5, labor_category="trim")

    # smoke detectors
    smokes = max(2, int(proj.floor_area_sqft / 500) + 1)
    add("smoke", smokes, fallback_name="Smoke Detector", unit_cost=22.0, labor_hours=0.3, labor_category="trim")

    est = Estimate(project_id=proj.id, name="Auto Takeoff", line_items=line_items, scope_of_work="Preliminary electrical takeoff generated from load calculation.")
    # labor summary
    from collections import defaultdict
    ls = defaultdict(float)
    for li in line_items:
        ls[li.get("labor_category", "rough_in")] += li.get("qty", 0) * li.get("labor_hours", 0)
    est.labor_summary = {k: round(v, 2) for k, v in ls.items()}
    _calc_totals(est, {})
    db.add(est)
    db.commit()
    db.refresh(est)
    return est

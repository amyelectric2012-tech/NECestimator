from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.calculations.nec220 import HVAC, Appliance, ProjectInput, calculate_all
from app.database import get_db
from app.models import LoadCalculation, Project
from app.schemas.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_input(p: Project) -> ProjectInput:
    hvac_raw = p.hvac or {}
    hvac = HVAC(
        cooling_va=hvac_raw.get("cooling_va", 0.0),
        heating_va=hvac_raw.get("heating_va", 0.0),
        heat_pump=hvac_raw.get("heat_pump", False),
        supplemental_heat_va=hvac_raw.get("supplemental_heat_va", 0.0),
        space_heating_units=hvac_raw.get("space_heating_units", 1),
        thermal_storage=hvac_raw.get("thermal_storage", False),
    )
    appliances = [Appliance(name=a.get("name", ""), va=a.get("va", 0.0), fastened=a.get("fastened", True)) for a in (p.appliances or [])]
    return ProjectInput(
        project_type=p.project_type,
        floor_area_sqft=p.floor_area_sqft,
        num_units=p.num_units,
        small_appliance_circuits=p.small_appliance_circuits,
        laundry_circuits=p.laundry_circuits,
        appliances=appliances,
        range_count=p.range_count,
        range_kw_each=p.range_kw_each,
        range_ratings_kw=p.range_ratings_kw or [],
        dryer_count=p.dryer_count,
        dryer_kw_each=p.dryer_kw_each,
        dryer_ratings_kw=p.dryer_ratings_kw or [],
        hvac=hvac,
        largest_motor_va=p.largest_motor_va,
        existing_service_amps=p.existing_service_amps,
    )


def _result_to_dict(r):
    import dataclasses
    d = dataclasses.asdict(r)
    # convert enums/none fine
    return d


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = Project(owner_id=user.id, **payload.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.get("", response_model=list[ProjectOut])
def list_projects(response: Response, db: Session = Depends(get_db), user=Depends(get_current_user), status: str | None = None, project_type: str | None = None, limit: int = 50, offset: int = 0):
    q = db.query(Project).filter(Project.owner_id == user.id)
    if status:
        q = q.filter(Project.status == status)
    if project_type:
        q = q.filter(Project.project_type == project_type)
    total = q.count()
    items = q.order_by(Project.created_at.desc()).offset(offset).limit(limit).all()
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(proj, k, v)
    db.commit()
    db.refresh(proj)
    return proj


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(proj)
    db.commit()
    return {"deleted": True}


@router.post("/{project_id}/calculate")
def calculate(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    inp = _to_input(proj)
    results = calculate_all(inp)
    # persist each method
    for method, res in results.items():
        lc = LoadCalculation(project_id=proj.id, method=method, results=_result_to_dict(res))
        db.add(lc)
    db.commit()
    return {"project_id": proj.id, "results": {m: _result_to_dict(r) for m, r in results.items()}}


@router.get("/{project_id}/load-calc")
def get_load_calc(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = db.query(LoadCalculation).filter(LoadCalculation.project_id == proj.id).order_by(LoadCalculation.created_at.desc()).all()
    # latest per method
    latest = {}
    for r in rows:
        if r.method not in latest:
            latest[r.method] = r
    return {"project_id": proj.id, "calculations": {m: {"id": lc.id, "method": lc.method, "results": lc.results, "created_at": lc.created_at} for m, lc in latest.items()}}

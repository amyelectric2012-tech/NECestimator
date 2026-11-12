from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Client, Estimate, EstimateActivity, Project, User
from app.schemas.schemas import EstimateActivityCreate, EstimateActivityOut, EstimateOut, EstimateUpdate

router = APIRouter(prefix="/crm", tags=["crm"])


def _owned_estimate(db: Session, estimate_id: str, user: User) -> Estimate:
    est = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    proj = db.query(Project).filter(Project.id == est.project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Not allowed")
    return est


@router.get("/pipeline")
def pipeline(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Estimate, Project, Client)
        .join(Project, Project.id == Estimate.project_id)
        .outerjoin(Client, Client.id == Estimate.client_id)
        .filter(Project.owner_id == user.id)
        .order_by(Estimate.updated_at.desc())
        .all()
    )
    out = []
    for est, proj, client in rows:
        out.append({
            "id": est.id,
            "project_id": proj.id,
            "project_name": proj.name,
            "client_id": (client.id if client else None),
            "client_name": (client.name if client else None),
            "name": est.name,
            "status": est.status or "draft",
            "probability": est.probability,
            "follow_up_date": est.follow_up_date,
            "next_action": est.next_action,
            "crm_notes": est.crm_notes,
            "last_contacted_at": est.last_contacted_at,
            "total_cost": est.total_cost,
            "total_materials": est.total_materials,
            "total_labor_hours": est.total_labor_hours,
            "created_at": est.created_at,
            "updated_at": est.updated_at,
        })
    return out


@router.patch("/estimates/{estimate_id}", response_model=EstimateOut)
def update_crm(estimate_id: str, payload: EstimateUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    est = _owned_estimate(db, estimate_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(est, k, v)
    # sync client_id from project if not set
    if est.client_id is None:
        proj = db.query(Project).filter(Project.id == est.project_id).first()
        if proj:
            est.client_id = proj.client_id
    db.commit()
    db.refresh(est)
    return est


@router.get("/estimates/{estimate_id}/activities", response_model=list[EstimateActivityOut])
def list_activities(estimate_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    est = _owned_estimate(db, estimate_id, user)
    return db.query(EstimateActivity).filter(EstimateActivity.estimate_id == est.id).order_by(EstimateActivity.created_at.desc()).all()


@router.post("/estimates/{estimate_id}/activities", response_model=EstimateActivityOut)
def add_activity(estimate_id: str, payload: EstimateActivityCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    est = _owned_estimate(db, estimate_id, user)
    act = EstimateActivity(estimate_id=est.id, owner_id=user.id, activity_type=payload.activity_type, body=payload.body)
    db.add(act)
    db.commit()
    db.refresh(act)
    return act
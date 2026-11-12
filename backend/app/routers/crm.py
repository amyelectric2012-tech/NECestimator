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


@router.get("/dashboard")
def dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.id
    clients = db.query(Client).filter(Client.owner_id == user_id).all()
    projects = db.query(Project).filter(Project.owner_id == user_id).all()
    project_ids = [p.id for p in projects]
    estimates = db.query(Estimate).filter(Estimate.project_id.in_(project_ids)).all() if project_ids else []
    project_by_id = {p.id: p for p in projects}
    client_by_id = {c.id: c for c in clients}

    by_status: dict[str, int] = {}
    for e in estimates:
        st = e.status or "draft"
        by_status[st] = by_status.get(st, 0) + 1

    open_statuses = {"draft", "sent", "viewed"}
    pipeline_value = sum((e.total_cost or 0) for e in estimates if (e.status or "draft") in open_statuses)
    accepted_value = sum((e.total_cost or 0) for e in estimates if (e.status or "draft") == "accepted")

    recent_estimates = sorted(estimates, key=lambda e: e.updated_at or e.created_at, reverse=True)[:10]
    recent_estimates_out = []
    for e in recent_estimates:
        proj = project_by_id.get(e.project_id)
        cli = client_by_id.get(e.client_id) if e.client_id else None
        recent_estimates_out.append({
            "id": e.id,
            "name": e.name,
            "status": e.status or "draft",
            "total_cost": e.total_cost,
            "project_id": e.project_id,
            "project_name": proj.name if proj else None,
            "client_name": cli.name if cli else None,
            "updated_at": e.updated_at or e.created_at,
        })

    recent_activities = (
        db.query(EstimateActivity, Estimate, Project)
        .join(Estimate, Estimate.id == EstimateActivity.estimate_id)
        .join(Project, Project.id == Estimate.project_id)
        .filter(Project.owner_id == user_id)
        .order_by(EstimateActivity.created_at.desc())
        .limit(20)
        .all()
    )
    activities_out = [
        {
            "id": a.id,
            "estimate_id": a.estimate_id,
            "estimate_name": est.name,
            "project_name": proj.name,
            "activity_type": a.activity_type,
            "body": a.body,
            "created_at": a.created_at,
        }
        for a, est, proj in recent_activities
    ]

    clients_out = []
    for c in clients:
        c_ests = [e for e in estimates if e.client_id == c.id]
        clients_out.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "estimates": len(c_ests),
            "value": round(sum((e.total_cost or 0) for e in c_ests), 2),
        })

    projects_out = []
    for p in projects:
        p_ests = [e for e in estimates if e.project_id == p.id]
        projects_out.append({
            "id": p.id,
            "name": p.name,
            "project_type": p.project_type,
            "status": p.status,
            "estimates": len(p_ests),
            "value": round(sum((e.total_cost or 0) for e in p_ests), 2),
        })

    return {
        "kpis": {
            "clients": len(clients),
            "projects": len(projects),
            "estimates": len(estimates),
            "open_estimates": sum(1 for e in estimates if (e.status or "draft") in open_statuses),
            "accepted_estimates": sum(1 for e in estimates if (e.status or "draft") == "accepted"),
            "pipeline_value": round(pipeline_value, 2),
            "accepted_value": round(accepted_value, 2),
        },
        "by_status": by_status,
        "recent_estimates": recent_estimates_out,
        "recent_activities": activities_out,
        "clients": clients_out,
        "projects": projects_out,
    }
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
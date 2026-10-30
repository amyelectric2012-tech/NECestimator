from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.models import Project, User
from app.models.takeoff import TakeoffItem
from app.schemas.takeoff import (
    TakeoffItemCreate,
    TakeoffItemResponse,
    TakeoffItemUpdate,
    TakeoffSummary,
)
from app.services.load_calc.engine import LoadCalcEngine
from app.services.load_calc.schemas import LoadCalcRequest
from app.services.takeoff.from_description import generate_from_description
from app.services.takeoff.generator import generate_takeoff_from_calculation
from app.services.takeoff.plan_reader import validate_plan_upload

router = APIRouter(prefix="/projects/{project_id}/takeoff-items", tags=["Takeoff"])


def _to_response(item: TakeoffItem) -> TakeoffItemResponse:
    uc = Decimal(str(item.unit_cost))
    total_mat = uc * Decimal(str(item.quantity))
    return TakeoffItemResponse(
        id=item.id,
        project_id=item.project_id,
        material_id=item.material_id,
        description=item.description,
        category=item.category,
        quantity=item.quantity,
        unit=item.unit,
        unit_cost=uc,
        labor_hours=item.labor_hours,
        notes=item.notes,
        is_auto_generated=item.is_auto_generated,
        total_material_cost=total_mat,
        total_labor_hours=item.quantity * item.labor_hours,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _summary(items: list[TakeoffItem], labor_rate: Decimal = Decimal("85.00"),
             contingency_percent: float = 5.0, tax_percent: float = 0.0) -> TakeoffSummary:
    resp = [_to_response(i) for i in items]
    total_mat = sum((Decimal(str(i.unit_cost)) * Decimal(str(i.quantity)) for i in items), Decimal(0))
    total_hours = sum(i.quantity * i.labor_hours for i in items)
    labor_cost = Decimal(str(total_hours)) * labor_rate
    subtotal = total_mat + labor_cost
    contingency = subtotal * Decimal(str(contingency_percent / 100.0))
    tax = total_mat * Decimal(str(tax_percent / 100.0))
    grand = subtotal + contingency + tax
    return TakeoffSummary(
        items=resp,
        total_material_cost=total_mat,
        total_labor_hours=total_hours,
        labor_rate=labor_rate,
        total_labor_cost=labor_cost,
        subtotal=subtotal,
        contingency_percent=contingency_percent,
        contingency_amount=contingency,
        tax_percent=tax_percent,
        tax_amount=tax,
        grand_total=grand,
    )


@router.post("/generate", response_model=list[TakeoffItemResponse])
def generate_takeoff(project_id: UUID, floor_area_sqft: float = 1500.0,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # run standard calc
    req = LoadCalcRequest(floor_area_sqft=floor_area_sqft or project.floor_area_sqft or 1500.0)
    # build from project data
    from app.services.load_calc.schemas import LoadCalcRequest as LCR
    req = LCR(
        project_type=project.project_type if project.project_type in ("single_family", "multi_family", "adu", "duplex") else "single_family",
        floor_area_sqft=project.floor_area_sqft or floor_area_sqft,
    )
    calc_results = LoadCalcEngine().calculate(req)
    std = calc_results[0]

    items = generate_takeoff_from_calculation(project.id, std, project.floor_area_sqft or floor_area_sqft)
    # persist
    created = []
    for it in items:
        row = TakeoffItem(
            project_id=str(project.id),
            description=it.description,
            category=it.category,
            quantity=it.quantity,
            unit=it.unit,
            unit_cost=it.unit_cost,
            labor_hours=it.labor_hours,
            is_auto_generated=it.is_auto_generated,
            notes=it.notes,
        )
        db.add(row)
        created.append(row)
    db.commit()
    for r in created:
        db.refresh(r)
    return [_to_response(r) for r in created]


@router.get("/", response_model=TakeoffSummary)
def get_takeoff(project_id: UUID, labor_rate: float | None = None, contingency_percent: float | None = None,
                tax_percent: float = 0.0, limit: int = 100, offset: int = 0,
                current_user: User = Depends(get_current_user), db: Session = Depends(get_db), response: Response = None):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    lr = labor_rate if labor_rate is not None else float(project.labor_rate or 85.0)
    cp = contingency_percent if contingency_percent is not None else float(project.contingency_percent or 5.0)
    all_items = db.query(TakeoffItem).filter(TakeoffItem.project_id == str(project_id)).all()
    total = len(all_items)
    summary = _summary(all_items, Decimal(str(lr)), cp, tax_percent)
    # paginate items in response
    summary.items = [_to_response(i) for i in all_items[offset:offset + limit]]
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return summary


@router.post("/", response_model=TakeoffItemResponse)
def add_takeoff_item(project_id: UUID, item: TakeoffItemCreate,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    row = TakeoffItem(
        project_id=str(project_id),
        material_id=str(item.material_id) if item.material_id else None,
        description=item.description,
        category=item.category,
        quantity=item.quantity,
        unit=item.unit,
        unit_cost=item.unit_cost,
        labor_hours=item.labor_hours,
        is_auto_generated=item.is_auto_generated,
        notes=item.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.patch("/{item_id}", response_model=TakeoffItemResponse)
def update_takeoff_item(project_id: UUID, item_id: UUID, payload: TakeoffItemUpdate,
                       current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    row = db.query(TakeoffItem).filter(TakeoffItem.id == str(item_id), TakeoffItem.project_id == str(project_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.patch("/settings", response_model=dict)
def update_takeoff_settings(project_id: UUID, labor_rate: float | None = None, contingency_percent: float | None = None,
                           current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if labor_rate is not None:
        project.labor_rate = labor_rate
    if contingency_percent is not None:
        project.contingency_percent = contingency_percent
    db.commit()
    return {"labor_rate": float(project.labor_rate), "contingency_percent": float(project.contingency_percent)}


@router.post("/from-plan", response_model=list[TakeoffItemResponse])
async def takeoff_from_plan(project_id: UUID, floor_area_sqft: float = 1500.0, file: UploadFile = File(...),
                           current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await validate_plan_upload(file)

    from app.services.load_calc.engine import LoadCalcEngine
    from app.services.load_calc.schemas import LoadCalcRequest
    req = LoadCalcRequest(
        project_type=project.project_type if project.project_type in ("single_family", "multi_family", "adu", "duplex") else "single_family",
        floor_area_sqft=project.floor_area_sqft or floor_area_sqft,
    )
    calc_results = LoadCalcEngine().calculate(req)
    std = calc_results[0]
    items = generate_takeoff_from_calculation(project.id, std, project.floor_area_sqft or floor_area_sqft)
    created = []
    for it in items:
        row = TakeoffItem(
            project_id=str(project.id),
            description=it.description + " (from plan)",
            category=it.category,
            quantity=it.quantity,
            unit=it.unit,
            unit_cost=it.unit_cost,
            labor_hours=it.labor_hours,
            is_auto_generated=True,
            notes=it.notes,
        )
        db.add(row)
        created.append(row)
    db.commit()
    for r in created:
        db.refresh(r)
    return [_to_response(r) for r in created]


@router.post("/from-description", response_model=dict)
def takeoff_from_description(project_id: UUID, description: str = Body(..., embed=True),
                            current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    items, refs = generate_from_description(project, description)
    created = []
    for it in items:
        row = TakeoffItem(
            project_id=str(project.id),
            description=it["description"],
            category=it["category"],
            quantity=it["quantity"],
            unit=it["unit"],
            unit_cost=it["unit_cost"],
            labor_hours=it["labor_hours"],
            is_auto_generated=it.get("is_auto_generated", False),
            notes=it.get("notes"),
        )
        db.add(row)
        created.append(row)
    db.commit()
    for r in created:
        db.refresh(r)
    return {
        "items": [_to_response(r).model_dump() for r in created],
        "nec_references": refs,
        "count": len(created),
    }


@router.delete("/{item_id}")
def delete_takeoff_item(project_id: UUID, item_id: UUID,
                       current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    row = db.query(TakeoffItem).filter(TakeoffItem.id == str(item_id), TakeoffItem.project_id == str(project_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Estimate, LoadCalculation, Project, TakeoffItem
from app.services.email import send_email_with_attachment
from app.services.pdf import generate_pdf

router = APIRouter(prefix="/projects", tags=["export"])


@router.get("/{project_id}/export-pdf")
def export_pdf(project_id: str, estimate_id: str | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    if estimate_id:
        est = db.query(Estimate).filter(Estimate.id == estimate_id, Estimate.project_id == proj.id).first()
    else:
        est = db.query(Estimate).filter(Estimate.project_id == proj.id).order_by(Estimate.created_at.desc()).first()
    if not est:
        raise HTTPException(status_code=404, detail="No estimate found; create one first")
    # load calcs
    rows = db.query(LoadCalculation).filter(LoadCalculation.project_id == proj.id).all()
    lc_map = {}
    for r in rows:
        if r.method not in lc_map:
            lc_map[r.method] = {"id": r.id, "method": r.method, "results": r.results}
    path = generate_pdf(proj, est, lc_map)
    est.pdf_path = path
    db.commit()
    return FileResponse(path, media_type="application/pdf", filename=f"{proj.name}.pdf")


@router.post("/{project_id}/estimate-from-takeoff")
def estimate_from_takeoff(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    items = db.query(TakeoffItem).filter(TakeoffItem.project_id == proj.id).all()
    if not items:
        raise HTTPException(status_code=400, detail="No takeoff items; generate takeoff first")
    line_items = []
    total_mat = 0.0
    total_hours = 0.0
    labor_summary = {}
    for it in items:
        lt = float(it.unit_cost) * it.quantity
        total_mat += lt
        total_hours += it.quantity * it.labor_hours
        labor_summary[it.category] = labor_summary.get(it.category, 0) + it.quantity * it.labor_hours
        line_items.append({
            "name": it.description,
            "qty": it.quantity,
            "unit": it.unit,
            "unit_cost": float(it.unit_cost),
            "line_total": lt,
            "labor_hours": it.labor_hours,
            "labor_category": it.category,
        })
    labor_rate = float(proj.labor_rate or 85.0)
    contingency_pct = (proj.contingency_percent or 5.0) / 100.0
    tax_pct = 0.0
    labor_cost = total_hours * labor_rate
    subtotal = total_mat + labor_cost
    contingency = subtotal * contingency_pct
    tax = total_mat * tax_pct
    grand = subtotal + contingency + tax
    est = Estimate(
        project_id=proj.id,
        name="Client Estimate",
        markup_pct=0.0,
        contingency_pct=contingency_pct,
        tax_pct=tax_pct,
        line_items=line_items,
        labor_summary=labor_summary,
        total_materials=total_mat,
        total_labor_hours=total_hours,
        total_cost=grand,
        scope_of_work="Residential electrical installation per NEC 2017.",
        assumptions="Preliminary estimate; field verification required. Unit costs editable.",
    )
    db.add(est)
    db.commit()
    db.refresh(est)
    rows = db.query(LoadCalculation).filter(LoadCalculation.project_id == proj.id).all()
    lc_map = {}
    for r in rows:
        if r.method not in lc_map:
            lc_map[r.method] = {"id": r.id, "method": r.method, "results": r.results}
    path = generate_pdf(proj, est, lc_map)
    est.pdf_path = path
    db.commit()
    return FileResponse(path, media_type="application/pdf", filename=f"{proj.name}_estimate.pdf")


@router.post("/{project_id}/email-estimate")
def email_estimate(project_id: str, to: str = Body(...), subject: str = Body("Your Electrical Estimate"), body: str = Body("Please find your estimate attached."),
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    items = db.query(TakeoffItem).filter(TakeoffItem.project_id == proj.id).all()
    if not items:
        raise HTTPException(status_code=400, detail="No takeoff items")
    # build estimate (reuse logic)
    line_items = []
    total_mat = 0.0
    total_hours = 0.0
    labor_summary = {}
    for it in items:
        lt = float(it.unit_cost) * it.quantity
        total_mat += lt
        total_hours += it.quantity * it.labor_hours
        labor_summary[it.category] = labor_summary.get(it.category, 0) + it.quantity * it.labor_hours
        line_items.append({"name": it.description, "qty": it.quantity, "unit": it.unit, "unit_cost": float(it.unit_cost), "line_total": lt, "labor_hours": it.labor_hours, "labor_category": it.category})
    labor_rate = float(proj.labor_rate or 85.0)
    contingency_pct = (proj.contingency_percent or 5.0) / 100.0
    labor_cost = total_hours * labor_rate
    subtotal = total_mat + labor_cost
    contingency = subtotal * contingency_pct
    grand = subtotal + contingency
    est = Estimate(project_id=proj.id, name="Client Estimate (emailed)", markup_pct=0.0, contingency_pct=contingency_pct, tax_pct=0.0,
                   line_items=line_items, labor_summary=labor_summary, total_materials=total_mat, total_labor_hours=total_hours, total_cost=grand,
                   scope_of_work="Residential electrical installation per NEC 2017.", assumptions="Preliminary estimate.")
    db.add(est)
    db.commit()
    db.refresh(est)
    rows = db.query(LoadCalculation).filter(LoadCalculation.project_id == proj.id).all()
    lc_map = {}
    for r in rows:
        if r.method not in lc_map:
            lc_map[r.method] = {"id": r.id, "method": r.method, "results": r.results}
    path = generate_pdf(proj, est, lc_map)
    est.pdf_path = path
    db.commit()
    try:
        send_email_with_attachment(to, subject, body, path, f"{proj.name}_estimate.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email failed: {e}")
    return {"sent": True, "to": to}

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Estimate, LoadCalculation, Project
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

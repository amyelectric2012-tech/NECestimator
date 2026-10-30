from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.models import Project, User
from app.services.load_calc.engine import LoadCalcEngine
from app.services.load_calc.schemas import LoadCalcRequest, LoadCalcResult

router = APIRouter(prefix="/calculations", tags=["Load Calculations"])


@router.post(
    "/",
    response_model=list[LoadCalcResult],
    summary="Run NEC Load Calculations",
    description="Calculates Standard Method + applicable Optional Methods (220.82 / 220.83 / 220.84)",
)
def run_load_calculation(
    data: LoadCalcRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        engine = LoadCalcEngine()
        return engine.calculate(data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calculation error: {e!s}",
        )


@router.post(
    "/projects/{project_id}",
    response_model=list[LoadCalcResult],
    summary="Run Load Calculations for an existing Project",
)
def run_load_calculation_for_project(
    project_id: UUID,
    data: LoadCalcRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        engine = LoadCalcEngine()
        results = engine.calculate(data)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calculation error: {e!s}",
        )

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import get_current_user
from app.models.models import User
from app.services.load_calc.engine import LoadCalcEngine
from app.services.load_calc.schemas import LoadCalcRequest, LoadCalcResult

router = APIRouter(prefix="/calculations", tags=["Load Calculations"])


@router.post(
    "",
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


from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.services.nec_calc import ampacity, conduit_fill, egc_size, gec_size, voltage_drop

router = APIRouter(prefix="/nec-calc", tags=["nec-calc"])


class AmpacityIn(BaseModel):
    size: str
    material: str = "cu"
    ambient_c: float = 30.0
    num_conductors: int = 3
    continuous: bool = False


class VoltageDropIn(BaseModel):
    size: str
    material: str = "cu"
    amps: float
    length_ft: float
    phase: int = 1
    max_percent: float = 3.0
    nominal_voltage: float | None = None


class ConduitFillIn(BaseModel):
    conductor_size: str
    num_conductors: int
    conduit_trade: str | None = None
    fill_percent: float = 40.0


class GroundingIn(BaseModel):
    service_conductor_size: str = "2/0"
    ocpd_amps: float = 200.0
    material: str = "cu"


@router.post("/ampacity")
def calc_ampacity(payload: AmpacityIn, user=Depends(get_current_user)):
    return ampacity(**payload.model_dump())


@router.post("/voltage-drop")
def calc_voltage_drop(payload: VoltageDropIn, user=Depends(get_current_user)):
    r = voltage_drop(payload.size, payload.material, payload.amps, payload.length_ft, payload.phase, payload.max_percent)
    if payload.nominal_voltage:
        # recompute percent against provided nominal voltage
        try:
            vd = r.get("value_volts")
            if vd is not None:
                r["value_percent"] = round((vd / payload.nominal_voltage) * 100.0, 2)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("voltage drop recompute failed: %s", e)
    return r


@router.post("/conduit-fill")
def calc_conduit_fill(payload: ConduitFillIn, user=Depends(get_current_user)):
    return conduit_fill(**payload.model_dump())


@router.post("/grounding")
def calc_grounding(payload: GroundingIn, user=Depends(get_current_user)):
    return {"gec": gec_size(payload.service_conductor_size, payload.material),
            "egc": egc_size(payload.ocpd_amps)}
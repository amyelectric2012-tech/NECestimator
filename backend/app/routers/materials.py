from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Material
from app.schemas.schemas import MaterialCreate, MaterialOut, MaterialUpdate

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[MaterialOut])
def list_materials(db: Session = Depends(get_db), user=Depends(get_current_user), category: str | None = None, q: str | None = None):
    query = db.query(Material)
    if category:
        query = query.filter(Material.category == category)
    if q:
        query = query.filter(Material.name.ilike(f"%{q}%"))
    return query.order_by(Material.category, Material.name).all()


@router.post("", response_model=MaterialOut)
def create_material(payload: MaterialCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    m = Material(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/{material_id}", response_model=MaterialOut)
def get_material(material_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
    return m


@router.put("/{material_id}", response_model=MaterialOut)
def update_material(material_id: str, payload: MaterialUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{material_id}")
def delete_material(material_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
    db.delete(m)
    db.commit()
    return {"deleted": True}

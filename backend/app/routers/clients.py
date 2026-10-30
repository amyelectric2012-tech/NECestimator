from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.models import Client, User
from app.schemas.clients import ClientCreate, ClientOut, ClientUpdate

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    q = db.query(Client).filter(Client.owner_id == current_user.id)
    total = q.count()
    items = q.order_by(Client.created_at.desc()).offset(offset).limit(limit).all()
    response.headers["X-Total-Count"] = str(total)
    return items


@router.post("", response_model=ClientOut)
def create_client(payload: ClientCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = Client(owner_id=current_user.id, **payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == str(client_id), Client.owner_id == current_user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    return c


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: UUID, payload: ClientUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == str(client_id), Client.owner_id == current_user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{client_id}")
def delete_client(client_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == str(client_id), Client.owner_id == current_user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(c)
    db.commit()
    return {"deleted": True}

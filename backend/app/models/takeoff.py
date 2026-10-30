import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class TakeoffItem(Base):
    __tablename__ = "takeoff_items"
    __table_args__ = (Index("ix_takeoff_items_project_id", "project_id"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    material_id = Column(UUID(as_uuid=False), ForeignKey("materials.id"), nullable=True)

    description = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    unit = Column(String(20), nullable=False, default="ea")

    unit_cost = Column(Numeric(10, 2), nullable=False, default=0)
    labor_hours = Column(Float, nullable=False, default=0.0)

    is_auto_generated = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

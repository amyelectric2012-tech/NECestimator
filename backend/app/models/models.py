import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_type = Column(String(50), default="single_family")
    status = Column(String(50), default="draft")
    floor_area_sqft = Column(Float, default=0.0)
    num_units = Column(Integer, default=1)
    small_appliance_circuits = Column(Integer, default=2)
    laundry_circuits = Column(Integer, default=1)
    appliances = Column(JSON, default=list)
    range_count = Column(Integer, default=0)
    range_kw_each = Column(Float, default=0.0)
    range_ratings_kw = Column(JSON, default=list)
    dryer_count = Column(Integer, default=0)
    dryer_kw_each = Column(Float, default=5.0)
    dryer_ratings_kw = Column(JSON, default=list)
    hvac = Column(JSON, default=dict)
    largest_motor_va = Column(Float, default=0.0)
    existing_service_amps = Column(Float, nullable=True)
    labor_rate = Column(Numeric(10, 2), default=85.00)
    contingency_percent = Column(Float, default=5.0)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="projects")
    load_calculations = relationship("LoadCalculation", back_populates="project", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="project", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materials"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    sku = Column(String(100), unique=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), index=True)
    unit = Column(String(50), default="ea")
    unit_cost = Column(Float, default=0.0)
    labor_hours = Column(Float, default=0.0)
    labor_category = Column(String(100), default="rough_in")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LaborRate(Base):
    __tablename__ = "labor_rates"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    category = Column(String(100), unique=True)
    hourly_rate = Column(Float, default=0.0)
    description = Column(Text, nullable=True)


class LoadCalculation(Base):
    __tablename__ = "load_calculations"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    method = Column(String(50), nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="load_calculations")


class Estimate(Base):
    __tablename__ = "estimates"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), default="Bid")
    markup_pct = Column(Float, default=0.10)
    contingency_pct = Column(Float, default=0.05)
    tax_pct = Column(Float, default=0.0)
    scope_of_work = Column(Text, nullable=True)
    assumptions = Column(Text, nullable=True)
    line_items = Column(JSON, default=list)
    labor_summary = Column(JSON, default=dict)
    total_materials = Column(Float, default=0.0)
    total_labor_hours = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    pdf_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project = relationship("Project", back_populates="estimates")

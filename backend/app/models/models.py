import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
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
    clients = relationship("Client", back_populates="owner", cascade="all, delete-orphan")


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (Index("ix_clients_owner_id", "owner_id"),)
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="clients")
    projects = relationship("Project", back_populates="client")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_owner_id", "owner_id"), Index("ix_projects_status", "status"),)
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
    jurisdiction = Column(String(100), nullable=True)
    nec_edition = Column(String(20), default="2017", server_default="2017", nullable=False)
    client_id = Column(UUID(as_uuid=False), ForeignKey("clients.id"), nullable=True)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="projects")
    client = relationship("Client", back_populates="projects")
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


class NECTable(Base):
    __tablename__ = "nec_tables"
    __table_args__ = (Index("ix_nec_tables_name", "name"),)
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    rows = Column(JSON, nullable=False)


class NECChunk(Base):
    __tablename__ = "nec_chunks"
    __table_args__ = (
        Index("ix_nec_chunks_chunk_index", "chunk_index"),
        Index("ix_nec_chunks_article", "article"),
        Index("ix_nec_chunks_section", "section"),
    )
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    chunk_index = Column(Integer, nullable=False)
    article = Column(String(20), nullable=True)
    section = Column(String(20), nullable=True)
    title = Column(String(300), nullable=True)
    section_title = Column(String(300), nullable=True)
    content = Column(Text, nullable=False)


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
    __table_args__ = (Index("ix_estimates_project_id", "project_id"), Index("ix_estimates_status", "status"), Index("ix_estimates_client_id", "client_id"),)
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    client_id = Column(UUID(as_uuid=False), ForeignKey("clients.id"), nullable=True)
    name = Column(String(255), default="Bid")
    markup_pct = Column(Float, default=0.10)
    contingency_pct = Column(Float, default=0.05)
    tax_pct = Column(Float, default=0.0)
    overhead_pct = Column(Float, default=0.10)
    # computed pricing (audit trail)
    direct_cost = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)
    contingency_cost = Column(Float, default=0.0)
    markup_cost = Column(Float, default=0.0)
    tax_cost = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    gross_margin = Column(Float, default=0.0)
    scope_of_work = Column(Text, nullable=True)
    assumptions = Column(Text, nullable=True)
    line_items = Column(JSON, default=list)
    labor_summary = Column(JSON, default=dict)
    total_materials = Column(Float, default=0.0)
    total_labor_hours = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    pdf_path = Column(String(500), nullable=True)
    # CRM fields
    status = Column(String(20), default="draft", server_default="draft", nullable=False)
    probability = Column(Float, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    next_action = Column(String(255), nullable=True)
    crm_notes = Column(Text, nullable=True)
    last_contacted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project = relationship("Project", back_populates="estimates")
    client = relationship("Client")
    activities = relationship("EstimateActivity", back_populates="estimate", cascade="all, delete-orphan", order_by="EstimateActivity.created_at.desc()")


class CalculationRecord(Base):
    __tablename__ = "calculation_records"
    __table_args__ = (Index("ix_calculation_records_project_id", "project_id"),)
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    method = Column(String(50), nullable=False)
    code_edition = Column(String(20), default="2017")
    engine_version = Column(String(30), default="nec220-1.0")
    inputs = Column(JSON, default=dict)
    outputs = Column(JSON, default=dict)
    warnings = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class EstimateActivity(Base):
    __tablename__ = "estimate_activities"
    __table_args__ = (Index("ix_estimate_activities_estimate_id", "estimate_id"),)
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    estimate_id = Column(UUID(as_uuid=False), ForeignKey("estimates.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    activity_type = Column(String(30), default="note")
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    estimate = relationship("Estimate", back_populates="activities")

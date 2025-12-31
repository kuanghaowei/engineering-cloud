"""Tenant Model"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.models.base import Base


class TenantType(str, enum.Enum):
    """Tenant type enumeration"""
    DESIGN = "design"
    CONSTRUCTION = "construction"
    OWNER = "owner"
    SUPERVISION = "supervision"


class Tenant(Base):
    """
    Tenant model representing an organization unit.
    
    Tenants provide data isolation for different organizations
    (design institutes, construction companies, owners, supervisors).
    """
    __tablename__ = 'tenants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    tenant_type = Column(
        SQLEnum(TenantType, name='tenant_type_enum', create_type=True),
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    projects = relationship("Project", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', type={self.tenant_type})>"

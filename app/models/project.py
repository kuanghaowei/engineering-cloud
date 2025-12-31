"""Project and ProjectMember Models"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.models.base import Base


class ProjectRole(str, enum.Enum):
    """Project member role enumeration"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    APPROVER = "approver"


class Project(Base):
    """
    Project model representing a top-level container.
    
    Projects contain repositories and manage member permissions.
    Each project belongs to a tenant.
    """
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    repositories = relationship(
        "Repository",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    members = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    workflows = relationship(
        "Workflow",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"


class ProjectMember(Base):
    """
    ProjectMember model representing user membership in a project.
    
    Defines the role-based access control (RBAC) for project resources.
    """
    __tablename__ = 'project_members'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    role = Column(
        SQLEnum(ProjectRole, name='project_role_enum', create_type=True),
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")
    
    def __repr__(self):
        return f"<ProjectMember(project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"

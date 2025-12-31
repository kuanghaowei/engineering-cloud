"""Workflow and WorkflowInstance Models"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.models.base import Base


class WorkflowStatus(str, enum.Enum):
    """Workflow instance status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class Workflow(Base):
    """
    Workflow model representing an approval process definition.
    
    Defines the structure and sequence of approval nodes
    for file version review and approval.
    """
    __tablename__ = 'workflows'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    nodes_config = Column(JSON, nullable=False)  # List of approval node configurations
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    project = relationship("Project", back_populates="workflows")
    instances = relationship(
        "WorkflowInstance",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Workflow(id={self.id}, name='{self.name}', project_id={self.project_id})>"


class WorkflowInstance(Base):
    """
    WorkflowInstance model representing a specific execution of a workflow.
    
    Tracks the progress of a file version through approval nodes,
    maintaining approval history and current state.
    """
    __tablename__ = 'workflow_instances'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey('workflows.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    file_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey('file_versions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    status = Column(
        SQLEnum(WorkflowStatus, name='workflow_status_enum', create_type=True),
        nullable=False,
        default=WorkflowStatus.PENDING
    )
    current_node_index = Column(Integer, default=0, nullable=False)
    approval_history = Column(JSON, default=list, nullable=False)  # List of approval records
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="instances")
    file_version = relationship("FileVersion", back_populates="workflow_instances")
    
    def __repr__(self):
        return f"<WorkflowInstance(id={self.id}, workflow_id={self.workflow_id}, status={self.status}, node={self.current_node_index})>"


# Performance optimization index
Index('idx_workflow_instances_status', WorkflowInstance.status, WorkflowInstance.current_node_index)

"""Repository Model"""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.models.base import Base


class Repository(Base):
    """
    Repository model representing a specialty domain container.
    
    Repositories organize files by professional domain
    (architecture, structure, MEP, etc.) within a project.
    """
    __tablename__ = 'repositories'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    specialty = Column(String(100))  # e.g., 'architecture', 'structure', 'mep'
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey('projects.id', ondelete='CASCADE'),
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
    project = relationship("Project", back_populates="repositories")
    file_nodes = relationship(
        "FileNode",
        back_populates="repository",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Repository(id={self.id}, name='{self.name}', specialty='{self.specialty}')>"

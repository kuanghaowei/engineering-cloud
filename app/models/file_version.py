"""FileVersion Model"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.models.base import Base


class FileVersion(Base):
    """
    FileVersion model representing a specific version of a file.
    
    Stores metadata about file versions including commit information
    and references to content chunks. Uses Git-like versioning.
    """
    __tablename__ = 'file_versions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_node_id = Column(
        UUID(as_uuid=True),
        ForeignKey('file_nodes.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    version_number = Column(Integer, nullable=False)
    commit_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256
    commit_message = Column(String(1000))
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    parent_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey('file_versions.id', ondelete='SET NULL'),
        nullable=True
    )
    file_size = Column(Integer, nullable=False)  # Total size in bytes
    chunk_refs = Column(JSON, nullable=False)  # List of {chunk_hash, chunk_index, chunk_size}
    is_locked = Column(Boolean, default=False, nullable=False)  # Locked after approval
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    file_node = relationship(
        "FileNode",
        back_populates="versions",
        foreign_keys=[file_node_id]
    )
    author = relationship("User", back_populates="file_versions")
    parent_version = relationship(
        "FileVersion",
        remote_side=[id],
        foreign_keys=[parent_version_id]
    )
    workflow_instances = relationship(
        "WorkflowInstance",
        back_populates="file_version",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<FileVersion(id={self.id}, file_node_id={self.file_node_id}, version={self.version_number}, commit={self.commit_hash[:8]})>"


# Performance optimization index
Index('idx_file_versions_file_node', FileVersion.file_node_id, FileVersion.version_number)

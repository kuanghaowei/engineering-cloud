"""FileNode Model"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.models.base import Base


class NodeType(str, enum.Enum):
    """File node type enumeration"""
    FILE = "file"
    DIRECTORY = "directory"


class FileNode(Base):
    """
    FileNode model representing a file or directory in the file system.
    
    Maintains a hierarchical tree structure with parent-child relationships.
    Files have associated versions, directories do not.
    """
    __tablename__ = 'file_nodes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    path = Column(String(2000), nullable=False)  # Full path from repository root
    node_type = Column(
        SQLEnum(NodeType, name='node_type_enum', create_type=True),
        nullable=False
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey('file_nodes.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    repository_id = Column(
        UUID(as_uuid=True),
        ForeignKey('repositories.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    current_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey('file_versions.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    repository = relationship("Repository", back_populates="file_nodes")
    parent = relationship(
        "FileNode",
        remote_side=[id],
        backref="children",
        foreign_keys=[parent_id]
    )
    versions = relationship(
        "FileVersion",
        back_populates="file_node",
        foreign_keys="FileVersion.file_node_id",
        cascade="all, delete-orphan"
    )
    current_version = relationship(
        "FileVersion",
        foreign_keys=[current_version_id],
        post_update=True
    )
    
    def __repr__(self):
        return f"<FileNode(id={self.id}, name='{self.name}', type={self.node_type}, path='{self.path}')>"


# Performance optimization index
Index('idx_file_nodes_repository_path', FileNode.repository_id, FileNode.path)

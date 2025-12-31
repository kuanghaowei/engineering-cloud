"""UploadSession Model"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.models.base import Base


class UploadStatus(str, enum.Enum):
    """Upload session status enumeration"""
    INITIALIZING = "initializing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadSession(Base):
    """
    UploadSession model for tracking chunked file uploads.
    
    Manages the state of multi-chunk uploads, tracking which chunks
    have been uploaded and coordinating the finalization process.
    """
    __tablename__ = 'upload_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_node_id = Column(
        UUID(as_uuid=True),
        ForeignKey('file_nodes.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    status = Column(
        SQLEnum(UploadStatus, name='upload_status_enum', create_type=True),
        nullable=False,
        default=UploadStatus.INITIALIZING
    )
    total_size = Column(Integer, nullable=False)  # Expected total file size
    uploaded_size = Column(Integer, default=0, nullable=False)  # Bytes uploaded so far
    total_chunks = Column(Integer, nullable=False)  # Expected number of chunks
    uploaded_chunks = Column(JSON, default=list, nullable=False)  # List of uploaded chunk hashes
    commit_message = Column(String(1000))
    error_message = Column(String(2000))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    file_node = relationship("FileNode", backref="upload_sessions")
    user = relationship("User", backref="upload_sessions")
    
    def __repr__(self):
        return f"<UploadSession(id={self.id}, file_node_id={self.file_node_id}, status={self.status}, progress={self.uploaded_size}/{self.total_size})>"
    
    @property
    def progress_percentage(self) -> float:
        """Calculate upload progress as percentage"""
        if self.total_size == 0:
            return 0.0
        return (self.uploaded_size / self.total_size) * 100

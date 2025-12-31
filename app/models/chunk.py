"""Chunk Model"""

from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.models.base import Base


class Chunk(Base):
    """
    Chunk model representing a content-addressable storage block.
    
    Implements deduplication through content hashing (SHA-256).
    Multiple file versions can reference the same chunk.
    """
    __tablename__ = 'chunks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )  # SHA-256 content hash
    chunk_size = Column(Integer, nullable=False)
    storage_key = Column(String(500), nullable=False)  # Object storage key
    ref_count = Column(Integer, default=1, nullable=False)  # Reference counting for GC
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Chunk(id={self.id}, hash={self.chunk_hash[:8]}, size={self.chunk_size}, refs={self.ref_count})>"


# Performance optimization index
Index('idx_chunks_hash', Chunk.chunk_hash)

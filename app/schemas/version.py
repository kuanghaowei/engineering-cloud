"""Version Control Schemas"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class ChunkReference(BaseModel):
    """Chunk reference in a file version"""
    chunk_hash: str = Field(..., description="SHA-256 hash of the chunk")
    chunk_index: int = Field(..., description="Index of the chunk in the file")
    chunk_size: int = Field(..., description="Size of the chunk in bytes")


class VersionResponse(BaseModel):
    """Response model for file version"""
    id: uuid.UUID
    file_node_id: uuid.UUID
    version_number: int
    commit_hash: str
    commit_message: Optional[str]
    author_id: uuid.UUID
    parent_version_id: Optional[uuid.UUID]
    file_size: int
    chunk_refs: List[Dict[str, Any]]
    is_locked: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class VersionHistoryResponse(BaseModel):
    """Response model for version history entry"""
    version_id: uuid.UUID
    version_number: int
    commit_hash: str
    commit_message: Optional[str]
    author_id: uuid.UUID
    file_size: int
    is_locked: bool
    created_at: str
    parent_version_id: Optional[uuid.UUID]


class CheckoutVersionRequest(BaseModel):
    """Request to checkout a specific version"""
    version_id: uuid.UUID = Field(..., description="ID of the version to checkout")


class CreateVersionRequest(BaseModel):
    """Request to create a new file version"""
    file_node_id: uuid.UUID
    chunk_refs: List[ChunkReference]
    commit_message: str
    parent_version_id: Optional[uuid.UUID] = None

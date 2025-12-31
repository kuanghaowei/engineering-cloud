"""Upload Schemas"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid


class InitUploadRequest(BaseModel):
    """Request to initialize an upload session"""
    file_node_id: uuid.UUID = Field(..., description="ID of the file node to upload to")
    total_size: int = Field(..., description="Total size of the file in bytes", gt=0)
    total_chunks: int = Field(..., description="Total number of chunks", gt=0)
    commit_message: Optional[str] = Field(None, description="Commit message for the version")


class InitUploadResponse(BaseModel):
    """Response from initializing an upload session"""
    session_id: uuid.UUID
    status: str
    message: str


class CheckChunksRequest(BaseModel):
    """Request to check which chunks exist"""
    chunk_hashes: List[str] = Field(..., description="List of SHA-256 chunk hashes to check")


class CheckChunksResponse(BaseModel):
    """Response with missing chunks"""
    missing_chunks: List[str] = Field(..., description="List of chunk hashes that need to be uploaded")
    total_checked: int
    missing_count: int


class UploadChunkResponse(BaseModel):
    """Response from uploading a chunk"""
    chunk_hash: str
    chunk_size: int
    uploaded: bool
    session_progress: float = Field(..., description="Upload progress percentage")


class ChunkRef(BaseModel):
    """Chunk reference for finalization"""
    chunk_hash: str
    chunk_index: int
    chunk_size: int


class FinalizeUploadRequest(BaseModel):
    """Request to finalize an upload session"""
    session_id: uuid.UUID
    chunk_refs: List[Dict[str, Any]] = Field(..., description="Ordered list of chunk references")
    parent_version_id: Optional[uuid.UUID] = Field(None, description="Parent version ID if updating")


class FinalizeUploadResponse(BaseModel):
    """Response from finalizing an upload"""
    version_id: uuid.UUID
    version_number: int
    commit_hash: str
    file_size: int
    message: str


class UploadProgressResponse(BaseModel):
    """Upload progress information"""
    session_id: str
    status: str
    total_size: int
    uploaded_size: int
    total_chunks: int
    uploaded_chunks_count: int
    progress_percentage: float
    created_at: str
    updated_at: str

"""Chunked Upload API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from sqlalchemy.orm import Session
from typing import List
import uuid
import hashlib

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.upload_service import UploadSessionService
from app.services.chunk_service import ChunkManager
from app.services.version_service import VersionService
from app.schemas.upload import (
    InitUploadRequest,
    InitUploadResponse,
    CheckChunksRequest,
    CheckChunksResponse,
    UploadChunkResponse,
    FinalizeUploadRequest,
    FinalizeUploadResponse,
    UploadProgressResponse
)

router = APIRouter(prefix="/v1/upload", tags=["upload"])


@router.post("/init", response_model=InitUploadResponse)
def initialize_upload(
    request: InitUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initialize a chunked upload session.
    
    Creates an upload session to track the progress of a multi-chunk upload.
    
    Validates: Requirements 13.1
    """
    upload_service = UploadSessionService(db)
    
    try:
        session = upload_service.initialize_upload(
            file_node_id=request.file_node_id,
            user_id=current_user.id,
            total_size=request.total_size,
            total_chunks=request.total_chunks,
            commit_message=request.commit_message
        )
        
        return InitUploadResponse(
            session_id=session.id,
            status=session.status.value,
            message="Upload session initialized successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/check", response_model=CheckChunksResponse)
def check_chunks(
    request: CheckChunksRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check which chunks already exist on the server.
    
    Allows clients to skip uploading chunks that are already stored
    (deduplication).
    
    Validates: Requirements 4.2, 13.2
    """
    chunk_manager = ChunkManager(db)
    
    missing_chunks = chunk_manager.check_chunks_exist(request.chunk_hashes)
    
    return CheckChunksResponse(
        missing_chunks=missing_chunks,
        total_checked=len(request.chunk_hashes),
        missing_count=len(missing_chunks)
    )


@router.put("/chunk", response_model=UploadChunkResponse)
async def upload_chunk(
    session_id: uuid.UUID = Body(...),
    chunk_hash: str = Body(...),
    chunk_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a single chunk.
    
    Stores the chunk in object storage and updates the upload session progress.
    
    Validates: Requirements 13.3
    """
    upload_service = UploadSessionService(db)
    chunk_manager = ChunkManager(db)
    
    # Verify session exists and belongs to user
    session = upload_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session {session_id} not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to upload to this session"
        )
    
    # Read chunk data
    chunk_data = await chunk_file.read()
    
    # Verify hash
    actual_hash = hashlib.sha256(chunk_data).hexdigest()
    if actual_hash != chunk_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chunk hash mismatch: expected {chunk_hash}, got {actual_hash}"
        )
    
    try:
        # Upload chunk (with deduplication)
        chunk = chunk_manager.upload_chunk(chunk_hash, chunk_data)
        
        # Update session progress
        session = upload_service.record_chunk_upload(
            session_id,
            chunk_hash,
            len(chunk_data)
        )
        
        return UploadChunkResponse(
            chunk_hash=chunk_hash,
            chunk_size=len(chunk_data),
            uploaded=True,
            session_progress=session.progress_percentage
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Mark session as failed
        upload_service.mark_failed(session_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload chunk: {str(e)}"
        )


@router.post("/finalize", response_model=FinalizeUploadResponse)
def finalize_upload(
    request: FinalizeUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finalize an upload session and create a file version.
    
    Verifies all chunks are uploaded and creates a new FileVersion record.
    
    Validates: Requirements 13.4
    """
    upload_service = UploadSessionService(db)
    version_service = VersionService(db)
    
    # Get session
    session = upload_service.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session {request.session_id} not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to finalize this session"
        )
    
    # Verify all chunks are uploaded
    if len(session.uploaded_chunks) != session.total_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not all chunks uploaded: {len(session.uploaded_chunks)}/{session.total_chunks}"
        )
    
    try:
        # Create file version
        version = version_service.create_version(
            file_node_id=session.file_node_id,
            chunk_refs=request.chunk_refs,
            commit_message=session.commit_message or "File uploaded",
            author_id=current_user.id,
            parent_version_id=request.parent_version_id
        )
        
        # Mark session as completed
        upload_service.mark_completed(request.session_id, version.id)
        
        return FinalizeUploadResponse(
            version_id=version.id,
            version_number=version.version_number,
            commit_hash=version.commit_hash,
            file_size=version.file_size,
            message="Upload finalized successfully"
        )
    except ValueError as e:
        upload_service.mark_failed(request.session_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        upload_service.mark_failed(request.session_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize upload: {str(e)}"
        )


@router.get("/session/{session_id}/progress", response_model=UploadProgressResponse)
def get_upload_progress(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get upload progress for a session.
    
    Returns current status and progress information.
    """
    upload_service = UploadSessionService(db)
    
    try:
        progress = upload_service.get_upload_progress(session_id)
        
        # Verify user has access
        session = upload_service.get_session(session_id)
        if session and session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this session"
            )
        
        return UploadProgressResponse(**progress)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/session/{session_id}")
def cancel_upload(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an upload session.
    """
    upload_service = UploadSessionService(db)
    
    # Verify session exists and belongs to user
    session = upload_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session {session_id} not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this session"
        )
    
    upload_service.cancel_session(session_id)
    
    return {
        "message": "Upload session cancelled successfully",
        "session_id": str(session_id)
    }

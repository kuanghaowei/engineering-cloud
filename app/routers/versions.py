"""Version Control API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.version_service import VersionService
from app.schemas.version import (
    VersionResponse,
    VersionHistoryResponse,
    CheckoutVersionRequest
)

router = APIRouter(prefix="/v1/versions", tags=["versions"])


@router.get("/{version_id}", response_model=VersionResponse)
def get_version(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific file version by ID.
    
    Validates: Requirements 5.4
    """
    version_service = VersionService(db)
    
    version = version_service.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version with ID {version_id} not found"
        )
    
    # TODO: Add permission check
    
    return VersionResponse(
        id=version.id,
        file_node_id=version.file_node_id,
        version_number=version.version_number,
        commit_hash=version.commit_hash,
        commit_message=version.commit_message,
        author_id=version.author_id,
        parent_version_id=version.parent_version_id,
        file_size=version.file_size,
        chunk_refs=version.chunk_refs,
        is_locked=version.is_locked,
        created_at=version.created_at
    )


@router.get("/file/{file_node_id}/history", response_model=List[VersionHistoryResponse])
def get_version_history(
    file_node_id: uuid.UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get version history for a file.
    
    Validates: Requirements 5.1
    """
    version_service = VersionService(db)
    
    # TODO: Add permission check
    
    history = version_service.get_version_history(file_node_id)
    
    return [
        VersionHistoryResponse(
            version_id=uuid.UUID(v["version_id"]),
            version_number=v["version_number"],
            commit_hash=v["commit_hash"],
            commit_message=v["commit_message"],
            author_id=uuid.UUID(v["author_id"]),
            file_size=v["file_size"],
            is_locked=v["is_locked"],
            created_at=v["created_at"],
            parent_version_id=uuid.UUID(v["parent_version_id"]) if v["parent_version_id"] else None
        )
        for v in history[:limit]
    ]


@router.post("/file/{file_node_id}/checkout")
def checkout_version(
    file_node_id: uuid.UUID,
    request: CheckoutVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Checkout a specific version (make it current).
    
    Validates: Requirements 5.4
    """
    version_service = VersionService(db)
    
    # TODO: Add permission check
    
    try:
        file_node = version_service.checkout_version(
            file_node_id,
            request.version_id
        )
        
        return {
            "message": "Version checked out successfully",
            "file_node_id": str(file_node.id),
            "current_version_id": str(file_node.current_version_id)
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{version_id}/chunks")
def get_version_chunks(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get chunk references for a version.
    
    Used by clients to download file content.
    """
    version_service = VersionService(db)
    
    # TODO: Add permission check
    
    try:
        chunks = version_service.get_version_chunks(version_id)
        return {
            "version_id": str(version_id),
            "chunks": chunks
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

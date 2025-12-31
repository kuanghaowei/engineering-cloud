"""Upload Session Management Service"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import uuid

from app.models.upload_session import UploadSession, UploadStatus
from app.models.file_node import FileNode
from app.models.user import User


class UploadSessionService:
    """
    Manages upload sessions for chunked file uploads.
    
    Tracks upload progress, coordinates chunk uploads, and handles
    session finalization.
    """
    
    def __init__(self, db: Session):
        """
        Initialize UploadSessionService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def initialize_upload(
        self,
        file_node_id: uuid.UUID,
        user_id: uuid.UUID,
        total_size: int,
        total_chunks: int,
        commit_message: Optional[str] = None
    ) -> UploadSession:
        """
        Initialize a new upload session.
        
        Args:
            file_node_id: ID of the file node being uploaded
            user_id: ID of the user performing the upload
            total_size: Total size of the file in bytes
            total_chunks: Expected number of chunks
            commit_message: Optional commit message for the version
            
        Returns:
            Created UploadSession object
            
        Raises:
            ValueError: If file_node or user doesn't exist
            
        Validates: Requirements 13.1
        """
        # Verify file node exists
        file_node = self.db.get(FileNode, file_node_id)
        if not file_node:
            raise ValueError(f"FileNode with ID {file_node_id} not found")
        
        # Verify user exists
        user = self.db.get(User, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Create upload session
        session = UploadSession(
            file_node_id=file_node_id,
            user_id=user_id,
            status=UploadStatus.IN_PROGRESS,
            total_size=total_size,
            uploaded_size=0,
            total_chunks=total_chunks,
            uploaded_chunks=[],
            commit_message=commit_message
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_session(self, session_id: uuid.UUID) -> Optional[UploadSession]:
        """
        Get an upload session by ID.
        
        Args:
            session_id: Upload session ID
            
        Returns:
            UploadSession object or None if not found
        """
        return self.db.get(UploadSession, session_id)
    
    def record_chunk_upload(
        self,
        session_id: uuid.UUID,
        chunk_hash: str,
        chunk_size: int
    ) -> UploadSession:
        """
        Record that a chunk has been uploaded.
        
        Updates the session's progress tracking.
        
        Args:
            session_id: Upload session ID
            chunk_hash: Hash of the uploaded chunk
            chunk_size: Size of the uploaded chunk in bytes
            
        Returns:
            Updated UploadSession object
            
        Raises:
            ValueError: If session doesn't exist or is not in progress
            
        Validates: Requirements 13.3
        """
        session = self.db.get(UploadSession, session_id)
        if not session:
            raise ValueError(f"Upload session {session_id} not found")
        
        if session.status not in [UploadStatus.INITIALIZING, UploadStatus.IN_PROGRESS]:
            raise ValueError(
                f"Cannot upload chunk to session in status {session.status}"
            )
        
        # Update progress
        if chunk_hash not in session.uploaded_chunks:
            session.uploaded_chunks = session.uploaded_chunks + [chunk_hash]
            session.uploaded_size += chunk_size
            session.status = UploadStatus.IN_PROGRESS
        
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_upload_progress(self, session_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get upload progress information.
        
        Args:
            session_id: Upload session ID
            
        Returns:
            Dictionary with progress information
            
        Raises:
            ValueError: If session doesn't exist
        """
        session = self.db.get(UploadSession, session_id)
        if not session:
            raise ValueError(f"Upload session {session_id} not found")
        
        return {
            "session_id": str(session.id),
            "status": session.status.value,
            "total_size": session.total_size,
            "uploaded_size": session.uploaded_size,
            "total_chunks": session.total_chunks,
            "uploaded_chunks_count": len(session.uploaded_chunks),
            "progress_percentage": session.progress_percentage,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
    
    def mark_completed(
        self,
        session_id: uuid.UUID,
        file_version_id: Optional[uuid.UUID] = None
    ) -> UploadSession:
        """
        Mark an upload session as completed.
        
        Args:
            session_id: Upload session ID
            file_version_id: Optional ID of the created file version
            
        Returns:
            Updated UploadSession object
            
        Raises:
            ValueError: If session doesn't exist
            
        Validates: Requirements 13.4
        """
        session = self.db.get(UploadSession, session_id)
        if not session:
            raise ValueError(f"Upload session {session_id} not found")
        
        session.status = UploadStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def mark_failed(
        self,
        session_id: uuid.UUID,
        error_message: str
    ) -> UploadSession:
        """
        Mark an upload session as failed.
        
        Args:
            session_id: Upload session ID
            error_message: Description of the failure
            
        Returns:
            Updated UploadSession object
            
        Raises:
            ValueError: If session doesn't exist
        """
        session = self.db.get(UploadSession, session_id)
        if not session:
            raise ValueError(f"Upload session {session_id} not found")
        
        session.status = UploadStatus.FAILED
        session.error_message = error_message
        session.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def cancel_session(self, session_id: uuid.UUID) -> UploadSession:
        """
        Cancel an upload session.
        
        Args:
            session_id: Upload session ID
            
        Returns:
            Updated UploadSession object
            
        Raises:
            ValueError: If session doesn't exist
        """
        session = self.db.get(UploadSession, session_id)
        if not session:
            raise ValueError(f"Upload session {session_id} not found")
        
        session.status = UploadStatus.CANCELLED
        session.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def list_user_sessions(
        self,
        user_id: uuid.UUID,
        status: Optional[UploadStatus] = None
    ) -> List[UploadSession]:
        """
        List upload sessions for a user.
        
        Args:
            user_id: User ID
            status: Optional status filter
            
        Returns:
            List of UploadSession objects
        """
        stmt = select(UploadSession).where(UploadSession.user_id == user_id)
        
        if status:
            stmt = stmt.where(UploadSession.status == status)
        
        stmt = stmt.order_by(UploadSession.created_at.desc())
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())

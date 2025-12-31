"""Version Control Service"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
import uuid
import hashlib
import json
from datetime import datetime

from app.models.file_version import FileVersion
from app.models.file_node import FileNode, NodeType
from app.models.user import User
from app.services.chunk_service import ChunkManager


class VersionService:
    """
    Manages file version control with Git-like semantics.
    
    Handles version creation, history tracking, and version retrieval.
    """
    
    def __init__(self, db: Session):
        """
        Initialize VersionService.
        
        Args:
            db: Database session
        """
        self.db = db
        self.chunk_manager = ChunkManager(db)
    
    def create_version(
        self,
        file_node_id: uuid.UUID,
        chunk_refs: List[Dict[str, Any]],
        commit_message: str,
        author_id: uuid.UUID,
        parent_version_id: Optional[uuid.UUID] = None
    ) -> FileVersion:
        """
        Create a new file version.
        
        Args:
            file_node_id: ID of the file node
            chunk_refs: List of chunk references with format:
                       [{"chunk_hash": str, "chunk_index": int, "chunk_size": int}, ...]
            commit_message: Commit message describing the changes
            author_id: ID of the user creating the version
            parent_version_id: Optional ID of the parent version
            
        Returns:
            Created FileVersion object
            
        Raises:
            ValueError: If file_node doesn't exist, is not a file, or author doesn't exist
            
        Validates: Requirements 5.1, 5.2, 5.3
        """
        # Verify file node exists and is a file
        file_node = self.db.get(FileNode, file_node_id)
        if not file_node:
            raise ValueError(f"FileNode with ID {file_node_id} not found")
        
        if file_node.node_type != NodeType.FILE:
            raise ValueError(f"FileNode {file_node_id} is not a file")
        
        # Verify author exists
        author = self.db.get(User, author_id)
        if not author:
            raise ValueError(f"User with ID {author_id} not found")
        
        # Verify all chunks exist
        chunk_hashes = [ref["chunk_hash"] for ref in chunk_refs]
        missing_chunks = self.chunk_manager.check_chunks_exist(chunk_hashes)
        if missing_chunks:
            raise ValueError(f"Missing chunks: {missing_chunks}")
        
        # Calculate total file size
        file_size = sum(ref["chunk_size"] for ref in chunk_refs)
        
        # Get next version number
        version_number = self._get_next_version_number(file_node_id)
        
        # Generate commit hash (SHA-256 of version metadata)
        commit_hash = self._generate_commit_hash(
            file_node_id,
            version_number,
            chunk_refs,
            author_id,
            datetime.utcnow()
        )
        
        # Create version
        version = FileVersion(
            file_node_id=file_node_id,
            version_number=version_number,
            commit_hash=commit_hash,
            commit_message=commit_message,
            author_id=author_id,
            parent_version_id=parent_version_id,
            file_size=file_size,
            chunk_refs=chunk_refs,
            is_locked=False
        )
        
        self.db.add(version)
        
        # Update file node's current version
        file_node.current_version_id = version.id
        file_node.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(version)
        
        return version
    
    def get_version(self, version_id: uuid.UUID) -> Optional[FileVersion]:
        """
        Get a file version by ID.
        
        Args:
            version_id: Version ID
            
        Returns:
            FileVersion object or None if not found
            
        Validates: Requirements 5.4
        """
        return self.db.get(FileVersion, version_id)
    
    def get_version_by_commit_hash(self, commit_hash: str) -> Optional[FileVersion]:
        """
        Get a file version by commit hash.
        
        Args:
            commit_hash: Commit hash
            
        Returns:
            FileVersion object or None if not found
        """
        stmt = select(FileVersion).where(FileVersion.commit_hash == commit_hash)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def list_versions(
        self,
        file_node_id: uuid.UUID,
        limit: Optional[int] = None
    ) -> List[FileVersion]:
        """
        List all versions of a file in reverse chronological order.
        
        Args:
            file_node_id: File node ID
            limit: Optional limit on number of versions to return
            
        Returns:
            List of FileVersion objects
            
        Validates: Requirements 5.1
        """
        stmt = select(FileVersion).where(
            FileVersion.file_node_id == file_node_id
        ).order_by(desc(FileVersion.version_number))
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def get_version_history(self, file_node_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get formatted version history for a file.
        
        Args:
            file_node_id: File node ID
            
        Returns:
            List of version information dictionaries
        """
        versions = self.list_versions(file_node_id)
        
        history = []
        for version in versions:
            history.append({
                "version_id": str(version.id),
                "version_number": version.version_number,
                "commit_hash": version.commit_hash,
                "commit_message": version.commit_message,
                "author_id": str(version.author_id),
                "file_size": version.file_size,
                "is_locked": version.is_locked,
                "created_at": version.created_at.isoformat(),
                "parent_version_id": str(version.parent_version_id) if version.parent_version_id else None
            })
        
        return history
    
    def checkout_version(
        self,
        file_node_id: uuid.UUID,
        version_id: uuid.UUID
    ) -> FileNode:
        """
        Checkout a specific version (make it the current version).
        
        Args:
            file_node_id: File node ID
            version_id: Version ID to checkout
            
        Returns:
            Updated FileNode object
            
        Raises:
            ValueError: If file_node or version doesn't exist, or version doesn't belong to file
        """
        # Verify file node exists
        file_node = self.db.get(FileNode, file_node_id)
        if not file_node:
            raise ValueError(f"FileNode with ID {file_node_id} not found")
        
        # Verify version exists
        version = self.db.get(FileVersion, version_id)
        if not version:
            raise ValueError(f"FileVersion with ID {version_id} not found")
        
        # Verify version belongs to this file
        if version.file_node_id != file_node_id:
            raise ValueError(
                f"Version {version_id} does not belong to file {file_node_id}"
            )
        
        # Update current version
        file_node.current_version_id = version_id
        file_node.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(file_node)
        
        return file_node
    
    def get_version_chunks(self, version_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get chunk references for a version.
        
        Args:
            version_id: Version ID
            
        Returns:
            List of chunk references
            
        Raises:
            ValueError: If version doesn't exist
        """
        version = self.db.get(FileVersion, version_id)
        if not version:
            raise ValueError(f"FileVersion with ID {version_id} not found")
        
        return version.chunk_refs
    
    def lock_version(self, version_id: uuid.UUID) -> FileVersion:
        """
        Lock a version (make it read-only).
        
        Used after approval workflows complete.
        
        Args:
            version_id: Version ID
            
        Returns:
            Updated FileVersion object
            
        Raises:
            ValueError: If version doesn't exist
        """
        version = self.db.get(FileVersion, version_id)
        if not version:
            raise ValueError(f"FileVersion with ID {version_id} not found")
        
        version.is_locked = True
        
        self.db.commit()
        self.db.refresh(version)
        
        return version
    
    def is_version_locked(self, version_id: uuid.UUID) -> bool:
        """
        Check if a version is locked.
        
        Args:
            version_id: Version ID
            
        Returns:
            True if locked, False otherwise
            
        Raises:
            ValueError: If version doesn't exist
        """
        version = self.db.get(FileVersion, version_id)
        if not version:
            raise ValueError(f"FileVersion with ID {version_id} not found")
        
        return version.is_locked
    
    def _get_next_version_number(self, file_node_id: uuid.UUID) -> int:
        """
        Get the next version number for a file.
        
        Args:
            file_node_id: File node ID
            
        Returns:
            Next version number (1 if no versions exist)
        """
        stmt = select(FileVersion).where(
            FileVersion.file_node_id == file_node_id
        ).order_by(desc(FileVersion.version_number)).limit(1)
        
        result = self.db.execute(stmt).scalar_one_or_none()
        
        if result:
            return result.version_number + 1
        return 1
    
    def _generate_commit_hash(
        self,
        file_node_id: uuid.UUID,
        version_number: int,
        chunk_refs: List[Dict[str, Any]],
        author_id: uuid.UUID,
        timestamp: datetime
    ) -> str:
        """
        Generate a unique commit hash for a version.
        
        Uses SHA-256 hash of version metadata.
        
        Args:
            file_node_id: File node ID
            version_number: Version number
            chunk_refs: Chunk references
            author_id: Author ID
            timestamp: Creation timestamp
            
        Returns:
            SHA-256 commit hash
            
        Validates: Requirements 5.2
        """
        # Create deterministic string from version metadata
        metadata = {
            "file_node_id": str(file_node_id),
            "version_number": version_number,
            "chunk_refs": chunk_refs,
            "author_id": str(author_id),
            "timestamp": timestamp.isoformat()
        }
        
        metadata_str = json.dumps(metadata, sort_keys=True)
        commit_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
        
        return commit_hash

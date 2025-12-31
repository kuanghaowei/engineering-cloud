"""Chunk Management Service"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
import hashlib

from app.models.chunk import Chunk
from app.storage.factory import get_storage_backend
from app.storage.backend import StorageBackendError, ObjectNotFoundError


class ChunkManager:
    """
    Manages file chunks with content-addressable storage (CAS).
    
    Implements chunk deduplication, existence checking, and retrieval.
    Chunks are stored using their SHA-256 hash as the key.
    """
    
    def __init__(self, db: Session):
        """
        Initialize ChunkManager.
        
        Args:
            db: Database session
        """
        self.db = db
        self.storage = get_storage_backend()
    
    def check_chunks_exist(self, chunk_hashes: List[str]) -> List[str]:
        """
        Check which chunks exist in the database.
        
        Args:
            chunk_hashes: List of SHA-256 chunk hashes to check
            
        Returns:
            List of chunk hashes that do NOT exist (missing chunks)
            
        Validates: Requirements 4.2
        """
        if not chunk_hashes:
            return []
        
        # Query database for existing chunks
        stmt = select(Chunk.chunk_hash).where(Chunk.chunk_hash.in_(chunk_hashes))
        result = self.db.execute(stmt)
        existing_hashes = {row[0] for row in result}
        
        # Return hashes that don't exist
        missing_hashes = [h for h in chunk_hashes if h not in existing_hashes]
        return missing_hashes
    
    def upload_chunk(self, chunk_hash: str, chunk_data: bytes) -> Chunk:
        """
        Upload a chunk to storage with deduplication.
        
        If a chunk with the same hash already exists, increments ref_count
        instead of storing duplicate data.
        
        Args:
            chunk_hash: SHA-256 hash of the chunk content
            chunk_data: Binary chunk data
            
        Returns:
            Chunk object (existing or newly created)
            
        Raises:
            ValueError: If chunk_hash doesn't match actual content hash
            StorageBackendError: If storage operation fails
            
        Validates: Requirements 4.4 (deduplication)
        """
        # Verify hash matches content
        actual_hash = hashlib.sha256(chunk_data).hexdigest()
        if actual_hash != chunk_hash:
            raise ValueError(
                f"Chunk hash mismatch: expected {chunk_hash}, got {actual_hash}"
            )
        
        # Check if chunk already exists (deduplication)
        stmt = select(Chunk).where(Chunk.chunk_hash == chunk_hash)
        existing_chunk = self.db.execute(stmt).scalar_one_or_none()
        
        if existing_chunk:
            # Chunk exists, increment reference count
            existing_chunk.ref_count += 1
            self.db.commit()
            return existing_chunk
        
        # Generate storage key from hash (content-addressable)
        storage_key = self._generate_storage_key(chunk_hash)
        
        # Store chunk in object storage
        try:
            success = self.storage.put_object(storage_key, chunk_data)
            if not success:
                raise StorageBackendError("Failed to store chunk in object storage")
        except Exception as e:
            raise StorageBackendError(f"Storage operation failed: {str(e)}")
        
        # Create chunk record in database
        chunk = Chunk(
            chunk_hash=chunk_hash,
            chunk_size=len(chunk_data),
            storage_key=storage_key,
            ref_count=1
        )
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        
        return chunk
    
    def get_chunk(self, chunk_hash: str) -> bytes:
        """
        Retrieve chunk data from storage.
        
        Args:
            chunk_hash: SHA-256 hash of the chunk to retrieve
            
        Returns:
            Binary chunk data
            
        Raises:
            ValueError: If chunk doesn't exist in database
            ObjectNotFoundError: If chunk exists in DB but not in storage
            StorageBackendError: If storage operation fails
        """
        # Get chunk metadata from database
        stmt = select(Chunk).where(Chunk.chunk_hash == chunk_hash)
        chunk = self.db.execute(stmt).scalar_one_or_none()
        
        if not chunk:
            raise ValueError(f"Chunk with hash {chunk_hash} not found in database")
        
        # Retrieve from object storage
        try:
            chunk_data = self.storage.get_object(chunk.storage_key)
            return chunk_data
        except ObjectNotFoundError:
            raise ObjectNotFoundError(
                f"Chunk {chunk_hash} exists in database but not in storage"
            )
        except Exception as e:
            raise StorageBackendError(f"Failed to retrieve chunk: {str(e)}")
    
    def get_chunk_by_hash(self, chunk_hash: str) -> Optional[Chunk]:
        """
        Get chunk metadata from database.
        
        Args:
            chunk_hash: SHA-256 hash of the chunk
            
        Returns:
            Chunk object or None if not found
        """
        stmt = select(Chunk).where(Chunk.chunk_hash == chunk_hash)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def decrement_ref_count(self, chunk_hash: str) -> None:
        """
        Decrement reference count for a chunk.
        
        Used when a file version is deleted. If ref_count reaches 0,
        the chunk can be garbage collected.
        
        Args:
            chunk_hash: SHA-256 hash of the chunk
        """
        stmt = select(Chunk).where(Chunk.chunk_hash == chunk_hash)
        chunk = self.db.execute(stmt).scalar_one_or_none()
        
        if chunk:
            chunk.ref_count = max(0, chunk.ref_count - 1)
            self.db.commit()
    
    def _generate_storage_key(self, chunk_hash: str) -> str:
        """
        Generate content-addressable storage key from hash.
        
        Uses Git-like directory structure: objects/ab/cd/abcd1234...
        
        Args:
            chunk_hash: SHA-256 hash (64 hex characters)
            
        Returns:
            Storage key path
            
        Validates: Requirements 6.3
        """
        if len(chunk_hash) < 4:
            raise ValueError("Chunk hash too short")
        
        # Create nested directory structure for better distribution
        return f"objects/{chunk_hash[:2]}/{chunk_hash[2:4]}/{chunk_hash}"

"""Abstract Storage Backend Interface"""

from abc import ABC, abstractmethod
from typing import Optional


class StorageBackend(ABC):
    """
    Abstract base class for object storage backends.
    
    This interface provides a unified API for storing and retrieving
    file chunks using content-addressable storage (CAS) pattern.
    Implementations include MinIO and Alibaba Cloud OSS.
    """
    
    @abstractmethod
    def put_object(self, key: str, data: bytes) -> bool:
        """
        Store an object in the storage backend.
        
        Args:
            key: Storage key (typically derived from content hash)
            data: Binary data to store
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            StorageBackendError: If storage operation fails
        """
        pass
    
    @abstractmethod
    def get_object(self, key: str) -> bytes:
        """
        Retrieve an object from the storage backend.
        
        Args:
            key: Storage key to retrieve
            
        Returns:
            Binary data of the object
            
        Raises:
            StorageBackendError: If storage operation fails
            ObjectNotFoundError: If object does not exist
        """
        pass
    
    @abstractmethod
    def delete_object(self, key: str) -> bool:
        """
        Delete an object from the storage backend.
        
        Args:
            key: Storage key to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            StorageBackendError: If storage operation fails
        """
        pass
    
    @abstractmethod
    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in the storage backend.
        
        Args:
            key: Storage key to check
            
        Returns:
            True if object exists, False otherwise
            
        Raises:
            StorageBackendError: If storage operation fails
        """
        pass


class StorageBackendError(Exception):
    """Base exception for storage backend errors"""
    pass


class ObjectNotFoundError(StorageBackendError):
    """Exception raised when an object is not found"""
    pass

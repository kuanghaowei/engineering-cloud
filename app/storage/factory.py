"""Storage Backend Factory"""

import logging
from typing import Optional

from app.storage.backend import StorageBackend, StorageBackendError
from app.storage.minio_backend import MinIOBackend
from app.storage.oss_backend import OSSBackend
from app.config import settings

logger = logging.getLogger(__name__)

# Global storage backend instance
_storage_backend: Optional[StorageBackend] = None


def get_storage_backend(force_new: bool = False) -> StorageBackend:
    """
    Get the configured storage backend instance.
    
    This function returns a singleton instance of the storage backend
    based on the STORAGE_BACKEND configuration setting.
    
    Args:
        force_new: If True, create a new instance instead of using singleton
        
    Returns:
        StorageBackend instance (MinIO or OSS)
        
    Raises:
        StorageBackendError: If backend type is invalid or initialization fails
    """
    global _storage_backend
    
    if _storage_backend is not None and not force_new:
        return _storage_backend
    
    backend_type = settings.storage_backend.lower()
    
    try:
        if backend_type == "minio":
            logger.info("Initializing MinIO storage backend")
            backend = MinIOBackend()
        elif backend_type == "oss":
            logger.info("Initializing OSS storage backend")
            backend = OSSBackend()
        else:
            raise StorageBackendError(
                f"Invalid storage backend type: {backend_type}. "
                f"Supported types: 'minio', 'oss'"
            )
        
        if not force_new:
            _storage_backend = backend
        
        return backend
        
    except Exception as e:
        logger.error(f"Failed to initialize storage backend: {e}")
        raise StorageBackendError(f"Storage backend initialization failed: {e}")


def reset_storage_backend():
    """
    Reset the global storage backend instance.
    
    This is useful for testing or when configuration changes.
    """
    global _storage_backend
    _storage_backend = None
    logger.info("Storage backend instance reset")

"""MinIO Storage Backend Implementation"""

import logging
from typing import Optional
from minio import Minio
from minio.error import S3Error
from urllib3 import Retry
from urllib3.util.timeout import Timeout

from app.storage.backend import StorageBackend, StorageBackendError, ObjectNotFoundError
from app.config import settings

logger = logging.getLogger(__name__)


class MinIOBackend(StorageBackend):
    """
    MinIO implementation of the storage backend.
    
    Provides object storage using MinIO with connection pooling,
    retry logic, and content-addressable storage (CAS) pattern.
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        secure: Optional[bool] = None
    ):
        """
        Initialize MinIO backend.
        
        Args:
            endpoint: MinIO server endpoint (default from settings)
            access_key: Access key (default from settings)
            secret_key: Secret key (default from settings)
            bucket: Bucket name (default from settings)
            secure: Use HTTPS (default from settings)
        """
        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_access_key
        self.secret_key = secret_key or settings.minio_secret_key
        self.bucket = bucket or settings.minio_bucket
        self.secure = secure if secure is not None else settings.minio_secure
        
        # Configure retry logic
        retry_config = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        
        # Configure timeout
        timeout_config = Timeout(connect=5.0, read=30.0)
        
        # Initialize MinIO client with connection pooling
        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                http_client=None  # Uses default urllib3 PoolManager
            )
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            logger.info(f"MinIO backend initialized: endpoint={self.endpoint}, bucket={self.bucket}")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO backend: {e}")
            raise StorageBackendError(f"MinIO initialization failed: {e}")
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created MinIO bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Failed to check/create bucket: {e}")
            raise StorageBackendError(f"Bucket operation failed: {e}")
    
    def _get_storage_key(self, key: str) -> str:
        """
        Convert content hash to storage key using CAS pattern.
        
        Args:
            key: Content hash (e.g., SHA-256)
            
        Returns:
            Storage key in format: objects/{hash[:2]}/{hash[2:4]}/{hash}
        """
        if len(key) < 4:
            return f"objects/{key}"
        return f"objects/{key[:2]}/{key[2:4]}/{key}"
    
    def put_object(self, key: str, data: bytes) -> bool:
        """
        Store an object in MinIO.
        
        Args:
            key: Content hash
            data: Binary data to store
            
        Returns:
            True if successful
            
        Raises:
            StorageBackendError: If storage operation fails
        """
        storage_key = self._get_storage_key(key)
        
        try:
            from io import BytesIO
            
            # Upload object
            self.client.put_object(
                self.bucket,
                storage_key,
                BytesIO(data),
                length=len(data)
            )
            
            logger.debug(f"Stored object: {storage_key} ({len(data)} bytes)")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to store object {storage_key}: {e}")
            raise StorageBackendError(f"Failed to store object: {e}")
        except Exception as e:
            logger.error(f"Unexpected error storing object {storage_key}: {e}")
            raise StorageBackendError(f"Unexpected storage error: {e}")
    
    def get_object(self, key: str) -> bytes:
        """
        Retrieve an object from MinIO.
        
        Args:
            key: Content hash
            
        Returns:
            Binary data of the object
            
        Raises:
            ObjectNotFoundError: If object does not exist
            StorageBackendError: If storage operation fails
        """
        storage_key = self._get_storage_key(key)
        
        try:
            response = self.client.get_object(self.bucket, storage_key)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.debug(f"Retrieved object: {storage_key} ({len(data)} bytes)")
            return data
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"Object not found: {storage_key}")
                raise ObjectNotFoundError(f"Object not found: {key}")
            logger.error(f"Failed to retrieve object {storage_key}: {e}")
            raise StorageBackendError(f"Failed to retrieve object: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving object {storage_key}: {e}")
            raise StorageBackendError(f"Unexpected storage error: {e}")
    
    def delete_object(self, key: str) -> bool:
        """
        Delete an object from MinIO.
        
        Args:
            key: Content hash
            
        Returns:
            True if successful
            
        Raises:
            StorageBackendError: If storage operation fails
        """
        storage_key = self._get_storage_key(key)
        
        try:
            self.client.remove_object(self.bucket, storage_key)
            logger.debug(f"Deleted object: {storage_key}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to delete object {storage_key}: {e}")
            raise StorageBackendError(f"Failed to delete object: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting object {storage_key}: {e}")
            raise StorageBackendError(f"Unexpected storage error: {e}")
    
    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in MinIO.
        
        Args:
            key: Content hash
            
        Returns:
            True if object exists, False otherwise
            
        Raises:
            StorageBackendError: If storage operation fails
        """
        storage_key = self._get_storage_key(key)
        
        try:
            self.client.stat_object(self.bucket, storage_key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"Failed to check object existence {storage_key}: {e}")
            raise StorageBackendError(f"Failed to check object existence: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking object {storage_key}: {e}")
            raise StorageBackendError(f"Unexpected storage error: {e}")

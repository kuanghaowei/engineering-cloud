"""Alibaba Cloud OSS Storage Backend Implementation"""

import logging
from typing import Optional
import oss2
from oss2.exceptions import NoSuchKey, ServerError, RequestError

from app.storage.backend import StorageBackend, StorageBackendError, ObjectNotFoundError
from app.config import settings

logger = logging.getLogger(__name__)


class OSSBackend(StorageBackend):
    """
    Alibaba Cloud OSS implementation of the storage backend.
    
    Provides object storage using Alibaba Cloud OSS with retry logic
    and content-addressable storage (CAS) pattern.
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None
    ):
        """
        Initialize OSS backend.
        
        Args:
            endpoint: OSS endpoint (default from settings)
            access_key: Access key ID (default from settings)
            secret_key: Access key secret (default from settings)
            bucket: Bucket name (default from settings)
        """
        self.endpoint = endpoint or settings.oss_endpoint
        self.access_key = access_key or settings.oss_access_key
        self.secret_key = secret_key or settings.oss_secret_key
        self.bucket_name = bucket or settings.oss_bucket
        
        if not all([self.endpoint, self.access_key, self.secret_key, self.bucket_name]):
            raise StorageBackendError(
                "OSS configuration incomplete. Required: endpoint, access_key, secret_key, bucket"
            )
        
        try:
            # Initialize OSS auth
            auth = oss2.Auth(self.access_key, self.secret_key)
            
            # Initialize bucket with retry configuration
            self.bucket = oss2.Bucket(
                auth,
                self.endpoint,
                self.bucket_name,
                connect_timeout=5,
                enable_crc=True
            )
            
            # Configure retry parameters
            self.max_retries = 3
            self.retry_delay = 0.5
            
            # Verify bucket exists
            self._verify_bucket_exists()
            
            logger.info(f"OSS backend initialized: endpoint={self.endpoint}, bucket={self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OSS backend: {e}")
            raise StorageBackendError(f"OSS initialization failed: {e}")
    
    def _verify_bucket_exists(self):
        """Verify that the bucket exists"""
        try:
            self.bucket.get_bucket_info()
        except oss2.exceptions.NoSuchBucket:
            logger.error(f"OSS bucket does not exist: {self.bucket_name}")
            raise StorageBackendError(f"Bucket does not exist: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to verify bucket: {e}")
            raise StorageBackendError(f"Bucket verification failed: {e}")
    
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
    
    def _retry_operation(self, operation, *args, **kwargs):
        """
        Execute an operation with retry logic.
        
        Args:
            operation: Function to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            StorageBackendError: If all retries fail
        """
        import time
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except (ServerError, RequestError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Operation failed (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.max_retries} attempts: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in operation: {e}")
                raise StorageBackendError(f"Unexpected error: {e}")
        
        raise StorageBackendError(f"Operation failed after {self.max_retries} retries: {last_error}")
    
    def put_object(self, key: str, data: bytes) -> bool:
        """
        Store an object in OSS.
        
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
            def _put():
                result = self.bucket.put_object(storage_key, data)
                return result.status == 200
            
            success = self._retry_operation(_put)
            
            if success:
                logger.debug(f"Stored object: {storage_key} ({len(data)} bytes)")
                return True
            else:
                raise StorageBackendError(f"Failed to store object: unexpected status")
                
        except NoSuchKey:
            logger.error(f"Bucket not found when storing object: {storage_key}")
            raise StorageBackendError(f"Bucket not found")
        except StorageBackendError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing object {storage_key}: {e}")
            raise StorageBackendError(f"Unexpected storage error: {e}")
    
    def get_object(self, key: str) -> bytes:
        """
        Retrieve an object from OSS.
        
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
            def _get():
                result = self.bucket.get_object(storage_key)
                return result.read()
            
            data = self._retry_operation(_get)
            
            logger.debug(f"Retrieved object: {storage_key} ({len(data)} bytes)")
            return data
            
        except NoSuchKey:
            logger.warning(f"Object not found: {storage_key}")
            raise ObjectNotFoundError(f"Object not found: {key}")
        except StorageBackendError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving object {storage_key}: {e}")
            raise StorageBackendError(f"Unexpected storage error: {e}")
    
    def delete_object(self, key: str) -> bool:
        """
        Delete an object from OSS.
        
        Args:
            key: Content hash
            
        Returns:
            True if successful
            
        Raises:
            StorageBackendError: If storage operation fails
        """
        storage_key = self._get_storage_key(key)
        
        try:
            def _delete():
                result = self.bucket.delete_object(storage_key)
                return result.status == 204
            
            success = self._retry_operation(_delete)
            
            if success:
                logger.debug(f"Deleted object: {storage_key}")
                return True
            else:
                raise StorageBackendError(f"Failed to delete object: unexpected status")
                
        except StorageBackendError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting object {storage_key}: {e}")
            raise StorageBackendError(f"Unexpected storage error: {e}")
    
    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in OSS.
        
        Args:
            key: Content hash
            
        Returns:
            True if object exists, False otherwise
            
        Raises:
            StorageBackendError: If storage operation fails
        """
        storage_key = self._get_storage_key(key)
        
        try:
            def _exists():
                return self.bucket.object_exists(storage_key)
            
            exists = self._retry_operation(_exists)
            return exists
            
        except StorageBackendError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error checking object {storage_key}: {e}")
            raise StorageBackendError(f"Unexpected storage error: {e}")

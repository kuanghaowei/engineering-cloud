"""Tests for Storage Backend Implementation"""

import pytest
import hashlib
from app.storage.backend import StorageBackend, StorageBackendError, ObjectNotFoundError
from app.storage.minio_backend import MinIOBackend
from app.storage.factory import get_storage_backend, reset_storage_backend


class TestStorageBackendInterface:
    """Test the abstract storage backend interface"""
    
    def test_storage_backend_is_abstract(self):
        """StorageBackend should be abstract and not instantiable"""
        with pytest.raises(TypeError):
            StorageBackend()


class TestMinIOBackend:
    """Test MinIO storage backend implementation"""
    
    @pytest.fixture
    def backend(self):
        """Create a MinIO backend instance for testing"""
        try:
            backend = MinIOBackend()
            yield backend
        except Exception as e:
            pytest.skip(f"MinIO not available: {e}")
    
    def test_put_and_get_object(self, backend):
        """Test storing and retrieving an object"""
        # Create test data
        test_data = b"Hello, MinIO!"
        test_hash = hashlib.sha256(test_data).hexdigest()
        
        # Store object
        result = backend.put_object(test_hash, test_data)
        assert result is True
        
        # Retrieve object
        retrieved_data = backend.get_object(test_hash)
        assert retrieved_data == test_data
        
        # Clean up
        backend.delete_object(test_hash)
    
    def test_object_exists(self, backend):
        """Test checking if an object exists"""
        # Create test data
        test_data = b"Existence test"
        test_hash = hashlib.sha256(test_data).hexdigest()
        
        # Object should not exist initially
        assert backend.object_exists(test_hash) is False
        
        # Store object
        backend.put_object(test_hash, test_data)
        
        # Object should now exist
        assert backend.object_exists(test_hash) is True
        
        # Clean up
        backend.delete_object(test_hash)
        
        # Object should not exist after deletion
        assert backend.object_exists(test_hash) is False
    
    def test_get_nonexistent_object(self, backend):
        """Test retrieving a non-existent object raises ObjectNotFoundError"""
        fake_hash = "nonexistent" + "0" * 54  # 64 char hash
        
        with pytest.raises(ObjectNotFoundError):
            backend.get_object(fake_hash)
    
    def test_delete_object(self, backend):
        """Test deleting an object"""
        # Create and store test data
        test_data = b"Delete me"
        test_hash = hashlib.sha256(test_data).hexdigest()
        backend.put_object(test_hash, test_data)
        
        # Verify it exists
        assert backend.object_exists(test_hash) is True
        
        # Delete it
        result = backend.delete_object(test_hash)
        assert result is True
        
        # Verify it's gone
        assert backend.object_exists(test_hash) is False
    
    def test_storage_key_format(self, backend):
        """Test that storage keys follow CAS pattern"""
        test_hash = "abcdef1234567890" * 4  # 64 char hash
        expected_key = f"objects/ab/cd/abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        
        storage_key = backend._get_storage_key(test_hash)
        assert storage_key == expected_key


class TestStorageFactory:
    """Test storage backend factory"""
    
    def test_get_storage_backend_returns_instance(self):
        """Test that factory returns a storage backend instance"""
        reset_storage_backend()
        backend = get_storage_backend()
        assert isinstance(backend, StorageBackend)
    
    def test_get_storage_backend_singleton(self):
        """Test that factory returns the same instance"""
        reset_storage_backend()
        backend1 = get_storage_backend()
        backend2 = get_storage_backend()
        assert backend1 is backend2
    
    def test_get_storage_backend_force_new(self):
        """Test that force_new creates a new instance"""
        reset_storage_backend()
        backend1 = get_storage_backend()
        backend2 = get_storage_backend(force_new=True)
        assert backend1 is not backend2
    
    def test_reset_storage_backend(self):
        """Test resetting the storage backend"""
        reset_storage_backend()
        backend1 = get_storage_backend()
        reset_storage_backend()
        backend2 = get_storage_backend()
        assert backend1 is not backend2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

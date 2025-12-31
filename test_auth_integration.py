"""Integration tests for authentication endpoints"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.tenant import Tenant, TenantType
from app.models.user import User
from app.config import settings


# Test database URL (use a separate test database)
TEST_DATABASE_URL = settings.database_url.replace("/aec_platform", "/aec_platform_test")

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def override_get_db():
    """Override database dependency for testing"""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="function")
async def setup_database():
    """Setup test database before each test"""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a test tenant
    async with TestSessionLocal() as session:
        tenant = Tenant(
            name="Test Design Institute",
            tenant_type=TenantType.DESIGN
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        tenant_id = tenant.id
    
    yield tenant_id
    
    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_user_registration(setup_database):
    """Test user registration endpoint"""
    tenant_id = setup_database
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test User",
                "tenant_id": str(tenant_id)
            }
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["tenant_id"] == str(tenant_id)
    assert "id" in data


@pytest.mark.asyncio
async def test_user_login(setup_database):
    """Test user login endpoint"""
    tenant_id = setup_database
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First register a user
        await client.post(
            "/v1/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "loginpass123",
                "full_name": "Login User",
                "tenant_id": str(tenant_id)
            }
        )
        
        # Then login
        response = await client.post(
            "/v1/auth/login",
            json={
                "username": "loginuser",
                "password": "loginpass123"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_get_current_user(setup_database):
    """Test getting current user information"""
    tenant_id = setup_database
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register and login
        await client.post(
            "/v1/auth/register",
            json={
                "username": "currentuser",
                "email": "current@example.com",
                "password": "currentpass123",
                "full_name": "Current User",
                "tenant_id": str(tenant_id)
            }
        )
        
        login_response = await client.post(
            "/v1/auth/login",
            json={
                "username": "currentuser",
                "password": "currentpass123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Get current user info
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "currentuser"
    assert data["email"] == "current@example.com"
    assert data["tenant_id"] == str(tenant_id)


@pytest.mark.asyncio
async def test_authentication_required(setup_database):
    """Test that protected endpoints require authentication"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try to access protected endpoint without token
        response = await client.get("/v1/auth/me")
    
    assert response.status_code == 403  # No credentials provided


@pytest.mark.asyncio
async def test_invalid_credentials(setup_database):
    """Test login with invalid credentials"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrongpassword"
            }
        )
    
    assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

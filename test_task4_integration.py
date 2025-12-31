"""
Integration tests for Task 4: Tenant and Project Management

Tests the tenant management, project management, and permission services.
"""

import pytest
import pytest_asyncio
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.models.tenant import Tenant, TenantType
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectRole
from app.services.tenant_service import TenantService
from app.services.project_service import ProjectService
from app.services.permission_service import PermissionService, Action
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.permission import ProjectMemberAdd, ProjectMemberUpdate
from app.auth import get_password_hash


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://aec_user:aec_password@localhost:5432/aec_platform_test"

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a test database session"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.mark.asyncio
async def test_tenant_crud_operations(db_session):
    """Test tenant CRUD operations"""
    # Create tenant
    tenant_data = TenantCreate(
        name="Test Design Institute",
        tenant_type=TenantType.DESIGN
    )
    tenant = await TenantService.create_tenant(db_session, tenant_data)
    
    assert tenant.id is not None
    assert tenant.name == "Test Design Institute"
    assert tenant.tenant_type == TenantType.DESIGN
    
    # Get tenant
    retrieved_tenant = await TenantService.get_tenant(db_session, tenant.id)
    assert retrieved_tenant is not None
    assert retrieved_tenant.id == tenant.id
    
    # List tenants
    tenants = await TenantService.list_tenants(db_session)
    assert len(tenants) == 1
    assert tenants[0].id == tenant.id
    
    # Update tenant
    update_data = TenantUpdate(name="Updated Design Institute")
    updated_tenant = await TenantService.update_tenant(db_session, tenant.id, update_data)
    assert updated_tenant.name == "Updated Design Institute"
    
    # Delete tenant
    deleted = await TenantService.delete_tenant(db_session, tenant.id)
    assert deleted is True
    
    # Verify deletion
    retrieved_tenant = await TenantService.get_tenant(db_session, tenant.id)
    assert retrieved_tenant is None


@pytest.mark.asyncio
async def test_project_creation_with_owner(db_session):
    """Test that project creation assigns creator as owner (Property 4)"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
        tenant_id=tenant.id
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create project
    project_data = ProjectCreate(
        name="Test Project",
        description="A test project"
    )
    project = await ProjectService.create_project(db_session, project_data, user)
    
    assert project.id is not None
    assert project.name == "Test Project"
    assert project.tenant_id == user.tenant_id
    
    # Verify creator is assigned as owner
    role = await PermissionService.get_user_role(db_session, user.id, project.id)
    assert role == ProjectRole.OWNER


@pytest.mark.asyncio
async def test_permission_matrix_enforcement(db_session):
    """Test RBAC permission enforcement (Property 5)"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create users
    owner_user = User(
        username="owner",
        email="owner@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Owner User",
        tenant_id=tenant.id
    )
    editor_user = User(
        username="editor",
        email="editor@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Editor User",
        tenant_id=tenant.id
    )
    viewer_user = User(
        username="viewer",
        email="viewer@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Viewer User",
        tenant_id=tenant.id
    )
    db_session.add_all([owner_user, editor_user, viewer_user])
    await db_session.flush()
    
    # Create project
    project_data = ProjectCreate(name="Test Project")
    project = await ProjectService.create_project(db_session, project_data, owner_user)
    
    # Add members with different roles
    await PermissionService.add_member(
        db_session,
        project.id,
        ProjectMemberAdd(user_id=editor_user.id, role=ProjectRole.EDITOR)
    )
    await PermissionService.add_member(
        db_session,
        project.id,
        ProjectMemberAdd(user_id=viewer_user.id, role=ProjectRole.VIEWER)
    )
    
    # Test owner permissions (should have all)
    assert await PermissionService.check_permission(db_session, owner_user.id, project.id, Action.READ) is True
    assert await PermissionService.check_permission(db_session, owner_user.id, project.id, Action.WRITE) is True
    assert await PermissionService.check_permission(db_session, owner_user.id, project.id, Action.DELETE) is True
    assert await PermissionService.check_permission(db_session, owner_user.id, project.id, Action.APPROVE) is True
    assert await PermissionService.check_permission(db_session, owner_user.id, project.id, Action.ADMIN) is True
    
    # Test editor permissions (read and write only)
    assert await PermissionService.check_permission(db_session, editor_user.id, project.id, Action.READ) is True
    assert await PermissionService.check_permission(db_session, editor_user.id, project.id, Action.WRITE) is True
    assert await PermissionService.check_permission(db_session, editor_user.id, project.id, Action.DELETE) is False
    assert await PermissionService.check_permission(db_session, editor_user.id, project.id, Action.APPROVE) is False
    assert await PermissionService.check_permission(db_session, editor_user.id, project.id, Action.ADMIN) is False
    
    # Test viewer permissions (read only)
    assert await PermissionService.check_permission(db_session, viewer_user.id, project.id, Action.READ) is True
    assert await PermissionService.check_permission(db_session, viewer_user.id, project.id, Action.WRITE) is False
    assert await PermissionService.check_permission(db_session, viewer_user.id, project.id, Action.DELETE) is False
    assert await PermissionService.check_permission(db_session, viewer_user.id, project.id, Action.APPROVE) is False
    assert await PermissionService.check_permission(db_session, viewer_user.id, project.id, Action.ADMIN) is False


@pytest.mark.asyncio
async def test_member_management(db_session):
    """Test adding, updating, and removing project members"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create users
    owner = User(
        username="owner",
        email="owner@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant.id
    )
    member = User(
        username="member",
        email="member@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant.id
    )
    db_session.add_all([owner, member])
    await db_session.flush()
    
    # Create project
    project_data = ProjectCreate(name="Test Project")
    project = await ProjectService.create_project(db_session, project_data, owner)
    
    # Add member as viewer
    added_member = await PermissionService.add_member(
        db_session,
        project.id,
        ProjectMemberAdd(user_id=member.id, role=ProjectRole.VIEWER)
    )
    assert added_member.role == ProjectRole.VIEWER
    
    # List members
    members = await PermissionService.list_members(db_session, project.id)
    assert len(members) == 2  # Owner + added member
    
    # Update member role
    updated_member = await PermissionService.update_member_role(
        db_session,
        project.id,
        member.id,
        ProjectMemberUpdate(role=ProjectRole.EDITOR)
    )
    assert updated_member.role == ProjectRole.EDITOR
    
    # Remove member
    removed = await PermissionService.remove_member(db_session, project.id, member.id)
    assert removed is True
    
    # Verify removal
    members = await PermissionService.list_members(db_session, project.id)
    assert len(members) == 1  # Only owner remains


@pytest.mark.asyncio
async def test_tenant_isolation(db_session):
    """Test that projects are isolated by tenant"""
    # Create two tenants
    tenant1 = Tenant(name="Tenant 1", tenant_type=TenantType.DESIGN)
    tenant2 = Tenant(name="Tenant 2", tenant_type=TenantType.CONSTRUCTION)
    db_session.add_all([tenant1, tenant2])
    await db_session.flush()
    
    # Create users for each tenant
    user1 = User(
        username="user1",
        email="user1@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant1.id
    )
    user2 = User(
        username="user2",
        email="user2@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant2.id
    )
    db_session.add_all([user1, user2])
    await db_session.flush()
    
    # Create projects for each tenant
    project1_data = ProjectCreate(name="Tenant 1 Project")
    project1 = await ProjectService.create_project(db_session, project1_data, user1)
    
    project2_data = ProjectCreate(name="Tenant 2 Project")
    project2 = await ProjectService.create_project(db_session, project2_data, user2)
    
    # Verify tenant isolation
    assert project1.tenant_id == tenant1.id
    assert project2.tenant_id == tenant2.id
    
    # List projects for tenant 1
    tenant1_projects = await ProjectService.list_projects(db_session, tenant1.id)
    assert len(tenant1_projects) == 1
    assert tenant1_projects[0].id == project1.id
    
    # List projects for tenant 2
    tenant2_projects = await ProjectService.list_projects(db_session, tenant2.id)
    assert len(tenant2_projects) == 1
    assert tenant2_projects[0].id == project2.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Simple integration tests for Task 4: Tenant and Project Management

Tests the tenant management, project management, and permission services
without requiring full database setup.
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

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
TEST_DATABASE_URL = "postgresql+asyncpg://aec_user:aec_password@localhost:5432/aec_platform"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session using existing database"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        # Rollback any changes
        await session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_service_create(db_session):
    """Test tenant creation"""
    tenant_data = TenantCreate(
        name=f"Test Tenant {uuid4().hex[:8]}",
        tenant_type=TenantType.DESIGN
    )
    tenant = await TenantService.create_tenant(db_session, tenant_data)
    
    assert tenant.id is not None
    assert tenant.name == tenant_data.name
    assert tenant.tenant_type == TenantType.DESIGN
    print(f"✓ Created tenant: {tenant.name} (ID: {tenant.id})")


@pytest.mark.asyncio
async def test_project_service_create_with_owner(db_session):
    """Test that project creation assigns creator as owner (Property 4)"""
    # Create tenant
    tenant_data = TenantCreate(
        name=f"Test Tenant {uuid4().hex[:8]}",
        tenant_type=TenantType.DESIGN
    )
    tenant = await TenantService.create_tenant(db_session, tenant_data)
    
    # Create user
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
        tenant_id=tenant.id
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create project
    project_data = ProjectCreate(
        name=f"Test Project {uuid4().hex[:8]}",
        description="A test project"
    )
    project = await ProjectService.create_project(db_session, project_data, user)
    
    assert project.id is not None
    assert project.tenant_id == user.tenant_id
    
    # Verify creator is assigned as owner (Property 4)
    role = await PermissionService.get_user_role(db_session, user.id, project.id)
    assert role == ProjectRole.OWNER
    print(f"✓ Created project with owner: {project.name} (ID: {project.id})")
    print(f"✓ Property 4 verified: Creator assigned as OWNER")


@pytest.mark.asyncio
async def test_permission_matrix(db_session):
    """Test RBAC permission matrix (Property 5)"""
    # Create tenant
    tenant_data = TenantCreate(
        name=f"Test Tenant {uuid4().hex[:8]}",
        tenant_type=TenantType.DESIGN
    )
    tenant = await TenantService.create_tenant(db_session, tenant_data)
    
    # Create owner user
    owner = User(
        username=f"owner_{uuid4().hex[:8]}",
        email=f"owner_{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant.id
    )
    db_session.add(owner)
    await db_session.flush()
    
    # Create project
    project_data = ProjectCreate(name=f"Test Project {uuid4().hex[:8]}")
    project = await ProjectService.create_project(db_session, project_data, owner)
    
    # Test owner permissions (should have all)
    assert await PermissionService.check_permission(db_session, owner.id, project.id, Action.READ) is True
    assert await PermissionService.check_permission(db_session, owner.id, project.id, Action.WRITE) is True
    assert await PermissionService.check_permission(db_session, owner.id, project.id, Action.DELETE) is True
    assert await PermissionService.check_permission(db_session, owner.id, project.id, Action.APPROVE) is True
    assert await PermissionService.check_permission(db_session, owner.id, project.id, Action.ADMIN) is True
    print(f"✓ Property 5 verified: OWNER has all permissions")
    
    # Create editor user
    editor = User(
        username=f"editor_{uuid4().hex[:8]}",
        email=f"editor_{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant.id
    )
    db_session.add(editor)
    await db_session.flush()
    
    # Add editor to project
    await PermissionService.add_member(
        db_session,
        project.id,
        ProjectMemberAdd(user_id=editor.id, role=ProjectRole.EDITOR)
    )
    
    # Test editor permissions (read and write only)
    assert await PermissionService.check_permission(db_session, editor.id, project.id, Action.READ) is True
    assert await PermissionService.check_permission(db_session, editor.id, project.id, Action.WRITE) is True
    assert await PermissionService.check_permission(db_session, editor.id, project.id, Action.DELETE) is False
    assert await PermissionService.check_permission(db_session, editor.id, project.id, Action.APPROVE) is False
    assert await PermissionService.check_permission(db_session, editor.id, project.id, Action.ADMIN) is False
    print(f"✓ Property 5 verified: EDITOR has READ and WRITE only")
    
    # Create viewer user
    viewer = User(
        username=f"viewer_{uuid4().hex[:8]}",
        email=f"viewer_{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant.id
    )
    db_session.add(viewer)
    await db_session.flush()
    
    # Add viewer to project
    await PermissionService.add_member(
        db_session,
        project.id,
        ProjectMemberAdd(user_id=viewer.id, role=ProjectRole.VIEWER)
    )
    
    # Test viewer permissions (read only)
    assert await PermissionService.check_permission(db_session, viewer.id, project.id, Action.READ) is True
    assert await PermissionService.check_permission(db_session, viewer.id, project.id, Action.WRITE) is False
    assert await PermissionService.check_permission(db_session, viewer.id, project.id, Action.DELETE) is False
    assert await PermissionService.check_permission(db_session, viewer.id, project.id, Action.APPROVE) is False
    assert await PermissionService.check_permission(db_session, viewer.id, project.id, Action.ADMIN) is False
    print(f"✓ Property 5 verified: VIEWER has READ only")


@pytest.mark.asyncio
async def test_member_management(db_session):
    """Test adding, updating, and removing project members"""
    # Create tenant
    tenant_data = TenantCreate(
        name=f"Test Tenant {uuid4().hex[:8]}",
        tenant_type=TenantType.DESIGN
    )
    tenant = await TenantService.create_tenant(db_session, tenant_data)
    
    # Create users
    owner = User(
        username=f"owner_{uuid4().hex[:8]}",
        email=f"owner_{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant.id
    )
    member = User(
        username=f"member_{uuid4().hex[:8]}",
        email=f"member_{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant.id
    )
    db_session.add_all([owner, member])
    await db_session.flush()
    
    # Create project
    project_data = ProjectCreate(name=f"Test Project {uuid4().hex[:8]}")
    project = await ProjectService.create_project(db_session, project_data, owner)
    
    # Add member as viewer
    added_member = await PermissionService.add_member(
        db_session,
        project.id,
        ProjectMemberAdd(user_id=member.id, role=ProjectRole.VIEWER)
    )
    assert added_member.role == ProjectRole.VIEWER
    print(f"✓ Added member as VIEWER")
    
    # Update member role to editor
    updated_member = await PermissionService.update_member_role(
        db_session,
        project.id,
        member.id,
        ProjectMemberUpdate(role=ProjectRole.EDITOR)
    )
    assert updated_member.role == ProjectRole.EDITOR
    print(f"✓ Updated member role to EDITOR")
    
    # List members
    members = await PermissionService.list_members(db_session, project.id)
    assert len(members) == 2  # Owner + member
    print(f"✓ Listed {len(members)} members")
    
    # Remove member
    removed = await PermissionService.remove_member(db_session, project.id, member.id)
    assert removed is True
    print(f"✓ Removed member from project")
    
    # Verify removal
    members = await PermissionService.list_members(db_session, project.id)
    assert len(members) == 1  # Only owner remains
    print(f"✓ Verified member removal")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

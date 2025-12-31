"""Basic tests for Task 6: File System and Repository Management"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.tenant import Tenant, TenantType
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.repository import Repository
from app.models.file_node import FileNode, NodeType
from app.services.repository_service import RepositoryService
from app.services.file_system_service import FileSystemService
from app.schemas.repository import RepositoryCreate, RepositoryUpdate
from app.schemas.file_node import FileNodeCreate, FileNodeMove


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
async def test_create_repository(db_session: AsyncSession):
    """Test creating a repository"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create project
    project = Project(
        name="Test Project",
        tenant_id=tenant.id
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create repository
    repo_data = RepositoryCreate(
        name="Architecture",
        description="Architecture repository",
        specialty="architecture"
    )
    
    repository = await RepositoryService.create_repository(
        db_session,
        project.id,
        repo_data
    )
    
    assert repository.id is not None
    assert repository.name == "Architecture"
    assert repository.specialty == "architecture"
    assert repository.project_id == project.id


@pytest.mark.asyncio
async def test_list_repositories(db_session: AsyncSession):
    """Test listing repositories"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create project
    project = Project(
        name="Test Project",
        tenant_id=tenant.id
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create multiple repositories
    for i in range(3):
        repo_data = RepositoryCreate(
            name=f"Repository {i}",
            specialty=f"specialty_{i}"
        )
        await RepositoryService.create_repository(
            db_session,
            project.id,
            repo_data
        )
    
    # List repositories
    repositories = await RepositoryService.list_repositories(
        db_session,
        project.id
    )
    
    assert len(repositories) == 3


@pytest.mark.asyncio
async def test_create_directory(db_session: AsyncSession):
    """Test creating a directory node"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create project
    project = Project(
        name="Test Project",
        tenant_id=tenant.id
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create repository
    repository = Repository(
        name="Test Repo",
        project_id=project.id
    )
    db_session.add(repository)
    await db_session.flush()
    
    # Create directory
    dir_data = FileNodeCreate(
        name="drawings",
        path="/drawings",
        node_type=NodeType.DIRECTORY,
        parent_id=None
    )
    
    directory = await FileSystemService.create_directory(
        db_session,
        repository.id,
        dir_data
    )
    
    assert directory.id is not None
    assert directory.name == "drawings"
    assert directory.path == "/drawings"
    assert directory.node_type == NodeType.DIRECTORY
    assert directory.repository_id == repository.id


@pytest.mark.asyncio
async def test_create_file(db_session: AsyncSession):
    """Test creating a file node"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create project
    project = Project(
        name="Test Project",
        tenant_id=tenant.id
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create repository
    repository = Repository(
        name="Test Repo",
        project_id=project.id
    )
    db_session.add(repository)
    await db_session.flush()
    
    # Create file
    file_data = FileNodeCreate(
        name="plan.dwg",
        path="/plan.dwg",
        node_type=NodeType.FILE,
        parent_id=None
    )
    
    file_node = await FileSystemService.create_file(
        db_session,
        repository.id,
        file_data
    )
    
    assert file_node.id is not None
    assert file_node.name == "plan.dwg"
    assert file_node.path == "/plan.dwg"
    assert file_node.node_type == NodeType.FILE
    assert file_node.repository_id == repository.id


@pytest.mark.asyncio
async def test_list_children(db_session: AsyncSession):
    """Test listing children of a directory"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create project
    project = Project(
        name="Test Project",
        tenant_id=tenant.id
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create repository
    repository = Repository(
        name="Test Repo",
        project_id=project.id
    )
    db_session.add(repository)
    await db_session.flush()
    
    # Create parent directory
    parent_data = FileNodeCreate(
        name="drawings",
        path="/drawings",
        node_type=NodeType.DIRECTORY,
        parent_id=None
    )
    parent = await FileSystemService.create_directory(
        db_session,
        repository.id,
        parent_data
    )
    
    # Create child files
    for i in range(3):
        child_data = FileNodeCreate(
            name=f"file{i}.dwg",
            path=f"/drawings/file{i}.dwg",
            node_type=NodeType.FILE,
            parent_id=parent.id
        )
        await FileSystemService.create_file(
            db_session,
            repository.id,
            child_data
        )
    
    # List children
    children = await FileSystemService.list_children(
        db_session,
        parent.id,
        repository.id
    )
    
    assert len(children) == 3
    assert all(child.parent_id == parent.id for child in children)


@pytest.mark.asyncio
async def test_move_node(db_session: AsyncSession):
    """Test moving a file node"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create project
    project = Project(
        name="Test Project",
        tenant_id=tenant.id
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create repository
    repository = Repository(
        name="Test Repo",
        project_id=project.id
    )
    db_session.add(repository)
    await db_session.flush()
    
    # Create file
    file_data = FileNodeCreate(
        name="plan.dwg",
        path="/plan.dwg",
        node_type=NodeType.FILE,
        parent_id=None
    )
    file_node = await FileSystemService.create_file(
        db_session,
        repository.id,
        file_data
    )
    
    # Move file
    move_data = FileNodeMove(
        new_path="/archive/plan.dwg",
        new_parent_id=None
    )
    moved_node = await FileSystemService.move_node(
        db_session,
        file_node.id,
        move_data
    )
    
    assert moved_node.path == "/archive/plan.dwg"


@pytest.mark.asyncio
async def test_delete_node(db_session: AsyncSession):
    """Test deleting a file node"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create project
    project = Project(
        name="Test Project",
        tenant_id=tenant.id
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create repository
    repository = Repository(
        name="Test Repo",
        project_id=project.id
    )
    db_session.add(repository)
    await db_session.flush()
    
    # Create file
    file_data = FileNodeCreate(
        name="plan.dwg",
        path="/plan.dwg",
        node_type=NodeType.FILE,
        parent_id=None
    )
    file_node = await FileSystemService.create_file(
        db_session,
        repository.id,
        file_data
    )
    
    # Delete file
    result = await FileSystemService.delete_node(
        db_session,
        file_node.id
    )
    
    assert result is True
    
    # Verify deletion
    deleted_node = await FileSystemService.get_file_node(
        db_session,
        file_node.id
    )
    assert deleted_node is None


@pytest.mark.asyncio
async def test_path_validation(db_session: AsyncSession):
    """Test path validation"""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        tenant_type=TenantType.DESIGN
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create project
    project = Project(
        name="Test Project",
        tenant_id=tenant.id
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create repository
    repository = Repository(
        name="Test Repo",
        project_id=project.id
    )
    db_session.add(repository)
    await db_session.flush()
    
    # Create parent directory
    parent_data = FileNodeCreate(
        name="drawings",
        path="/drawings",
        node_type=NodeType.DIRECTORY,
        parent_id=None
    )
    parent = await FileSystemService.create_directory(
        db_session,
        repository.id,
        parent_data
    )
    
    # Test valid path under parent
    is_valid = await FileSystemService.validate_path(
        db_session,
        repository.id,
        "/drawings/plan.dwg",
        parent.id
    )
    assert is_valid is True
    
    # Test invalid path (not under parent)
    is_valid = await FileSystemService.validate_path(
        db_session,
        repository.id,
        "/other/plan.dwg",
        parent.id
    )
    assert is_valid is False

"""Repository Router"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.schemas.repository import RepositoryCreate, RepositoryUpdate, RepositoryResponse
from app.services.repository_service import RepositoryService
from app.services.project_service import ProjectService
from app.auth import get_current_active_user
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/repositories", tags=["Repositories"])


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    project_id: UUID = Query(..., description="Project ID to create repository in"),
    repository_data: RepositoryCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new repository within a project.
    
    Args:
        project_id: Project UUID
        repository_data: Repository creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        RepositoryResponse: Created repository information
        
    Raises:
        HTTPException: If project not found or access denied
    """
    # Check if project exists and belongs to user's tenant
    project = await ProjectService.get_project(db, project_id)
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    if project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: project belongs to different tenant"
        )
    
    repository = await RepositoryService.create_repository(db, project_id, repository_data)
    return repository


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a repository by ID.
    
    Args:
        repository_id: Repository UUID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        RepositoryResponse: Repository information
        
    Raises:
        HTTPException: If repository not found or access denied
    """
    repository = await RepositoryService.get_repository(db, repository_id)
    
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {repository_id} not found"
        )
    
    # Check tenant isolation through project
    project = await ProjectService.get_project(db, repository.project_id)
    if project and project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: repository belongs to different tenant"
        )
    
    return repository


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    project_id: UUID = Query(..., description="Project ID to list repositories from"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all repositories for a project.
    
    Args:
        project_id: Project UUID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[RepositoryResponse]: List of repositories
        
    Raises:
        HTTPException: If project not found or access denied
    """
    # Check if project exists and belongs to user's tenant
    project = await ProjectService.get_project(db, project_id)
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    if project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: project belongs to different tenant"
        )
    
    repositories = await RepositoryService.list_repositories(db, project_id, skip, limit)
    return repositories


@router.put("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    repository_id: UUID,
    repository_data: RepositoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a repository.
    
    Args:
        repository_id: Repository UUID
        repository_data: Repository update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        RepositoryResponse: Updated repository information
        
    Raises:
        HTTPException: If repository not found or access denied
    """
    # Check if repository exists and belongs to user's tenant
    repository = await RepositoryService.get_repository(db, repository_id)
    
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {repository_id} not found"
        )
    
    # Check tenant isolation through project
    project = await ProjectService.get_project(db, repository.project_id)
    if project and project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: repository belongs to different tenant"
        )
    
    updated_repository = await RepositoryService.update_repository(db, repository_id, repository_data)
    return updated_repository


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a repository.
    
    Args:
        repository_id: Repository UUID
        db: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException: If repository not found or access denied
    """
    # Check if repository exists and belongs to user's tenant
    repository = await RepositoryService.get_repository(db, repository_id)
    
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {repository_id} not found"
        )
    
    # Check tenant isolation through project
    project = await ProjectService.get_project(db, repository.project_id)
    if project and project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: repository belongs to different tenant"
        )
    
    await RepositoryService.delete_repository(db, repository_id)

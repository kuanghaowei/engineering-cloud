"""Project Router"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import ProjectService
from app.auth import get_current_active_user
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new project.
    
    The creator is automatically assigned as project owner.
    
    Args:
        project_data: Project creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ProjectResponse: Created project information
    """
    project = await ProjectService.create_project(db, project_data, current_user)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a project by ID.
    
    Args:
        project_id: Project UUID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ProjectResponse: Project information
        
    Raises:
        HTTPException: If project not found
    """
    project = await ProjectService.get_project(db, project_id)
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Check tenant isolation
    if project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: project belongs to different tenant"
        )
    
    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all projects for the current user's tenant.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[ProjectResponse]: List of projects
    """
    projects = await ProjectService.list_projects(
        db, 
        current_user.tenant_id, 
        skip, 
        limit
    )
    return projects


@router.get("/me/projects", response_model=List[ProjectResponse])
async def list_my_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all projects where the current user is a member.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[ProjectResponse]: List of projects
    """
    projects = await ProjectService.list_user_projects(
        db, 
        current_user.id, 
        skip, 
        limit
    )
    return projects


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a project.
    
    Args:
        project_id: Project UUID
        project_data: Project update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ProjectResponse: Updated project information
        
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
    
    # Update project
    updated_project = await ProjectService.update_project(db, project_id, project_data)
    return updated_project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a project.
    
    Args:
        project_id: Project UUID
        db: Database session
        current_user: Current authenticated user
        
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
    
    await ProjectService.delete_project(db, project_id)

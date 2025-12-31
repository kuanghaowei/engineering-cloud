"""Permissions Router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.schemas.permission import (
    ProjectMemberAdd,
    ProjectMemberUpdate,
    ProjectMemberResponse,
    UserWithRole
)
from app.services.permission_service import PermissionService, Action
from app.services.project_service import ProjectService
from app.auth import get_current_active_user
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/projects", tags=["Permissions"])


async def verify_project_access(
    project_id: UUID,
    current_user: User,
    db: AsyncSession,
    required_action: str = Action.READ
) -> Project:
    """
    Verify that user has access to a project.
    
    Args:
        project_id: Project UUID
        current_user: Current authenticated user
        db: Database session
        required_action: Required action permission
        
    Returns:
        Project: The project if access is granted
        
    Raises:
        HTTPException: If project not found or access denied
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
    
    # Check permission
    has_permission = await PermissionService.check_permission(
        db, current_user.id, project_id, required_action
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: insufficient permissions (requires {required_action})"
        )
    
    return project


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_project_member(
    project_id: UUID,
    member_data: ProjectMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add a member to a project.
    
    Requires admin permission on the project.
    
    Args:
        project_id: Project UUID
        member_data: Member data (user_id and role)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ProjectMemberResponse: Created project member
        
    Raises:
        HTTPException: If project not found, access denied, or user not found
    """
    # Verify admin access
    await verify_project_access(project_id, current_user, db, Action.ADMIN)
    
    # Check if user exists and belongs to same tenant
    result = await db.execute(
        select(User).where(User.id == member_data.user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {member_data.user_id} not found"
        )
    
    if user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add user from different tenant"
        )
    
    # Add member
    try:
        member = await PermissionService.add_member(db, project_id, member_data)
        return member
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_project_members(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all members of a project.
    
    Requires read permission on the project.
    
    Args:
        project_id: Project UUID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[ProjectMemberResponse]: List of project members
        
    Raises:
        HTTPException: If project not found or access denied
    """
    # Verify read access
    await verify_project_access(project_id, current_user, db, Action.READ)
    
    # List members
    members = await PermissionService.list_members(db, project_id)
    return members


@router.put(
    "/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse
)
async def update_project_member_role(
    project_id: UUID,
    user_id: UUID,
    role_data: ProjectMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a member's role in a project.
    
    Requires admin permission on the project.
    
    Args:
        project_id: Project UUID
        user_id: User UUID
        role_data: New role data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ProjectMemberResponse: Updated project member
        
    Raises:
        HTTPException: If project not found, access denied, or member not found
    """
    # Verify admin access
    await verify_project_access(project_id, current_user, db, Action.ADMIN)
    
    # Update member role
    member = await PermissionService.update_member_role(
        db, project_id, user_id, role_data
    )
    
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} is not a member of project {project_id}"
        )
    
    return member


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove a member from a project.
    
    Requires admin permission on the project.
    
    Args:
        project_id: Project UUID
        user_id: User UUID
        db: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException: If project not found, access denied, or member not found
    """
    # Verify admin access
    await verify_project_access(project_id, current_user, db, Action.ADMIN)
    
    # Remove member
    removed = await PermissionService.remove_member(db, project_id, user_id)
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} is not a member of project {project_id}"
        )


@router.get("/{project_id}/members/me/role", response_model=dict)
async def get_my_role(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's role in a project.
    
    Args:
        project_id: Project UUID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: User's role information
        
    Raises:
        HTTPException: If project not found or user is not a member
    """
    # Verify project exists and belongs to user's tenant
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
    
    # Get user's role
    role = await PermissionService.get_user_role(db, current_user.id, project_id)
    
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this project"
        )
    
    return {
        "project_id": project_id,
        "user_id": current_user.id,
        "role": role
    }

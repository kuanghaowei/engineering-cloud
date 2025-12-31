"""Permission Service"""

from uuid import UUID
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User
from app.schemas.permission import ProjectMemberAdd, ProjectMemberUpdate
from app.logging_config import get_logger

logger = get_logger(__name__)


class Action:
    """Enum-like class for actions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    APPROVE = "approve"
    ADMIN = "admin"


class PermissionService:
    """Service for managing permissions and RBAC"""
    
    # Permission matrix as defined in design document
    PERMISSION_MATRIX = {
        ProjectRole.OWNER: {
            Action.READ, Action.WRITE, Action.DELETE, Action.APPROVE, Action.ADMIN
        },
        ProjectRole.EDITOR: {
            Action.READ, Action.WRITE
        },
        ProjectRole.VIEWER: {
            Action.READ
        },
        ProjectRole.APPROVER: {
            Action.READ, Action.APPROVE
        }
    }
    
    @staticmethod
    async def check_permission(
        db: AsyncSession,
        user_id: UUID,
        project_id: UUID,
        action: str
    ) -> bool:
        """
        Check if a user has permission to perform an action on a project.
        
        Implements Property 5: Role-based access control enforcement
        
        Args:
            db: Database session
            user_id: User UUID
            project_id: Project UUID
            action: Action to check (read, write, delete, approve, admin)
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        # Get user's role in the project
        result = await db.execute(
            select(ProjectMember)
            .where(
                and_(
                    ProjectMember.user_id == user_id,
                    ProjectMember.project_id == project_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None:
            return False
        
        # Check if role has permission for action
        allowed_actions = PermissionService.PERMISSION_MATRIX.get(member.role, set())
        return action in allowed_actions
    
    @staticmethod
    async def get_user_role(
        db: AsyncSession,
        user_id: UUID,
        project_id: UUID
    ) -> Optional[ProjectRole]:
        """
        Get a user's role in a project.
        
        Args:
            db: Database session
            user_id: User UUID
            project_id: Project UUID
            
        Returns:
            Optional[ProjectRole]: User's role if member, None otherwise
        """
        result = await db.execute(
            select(ProjectMember.role)
            .where(
                and_(
                    ProjectMember.user_id == user_id,
                    ProjectMember.project_id == project_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def add_member(
        db: AsyncSession,
        project_id: UUID,
        member_data: ProjectMemberAdd
    ) -> ProjectMember:
        """
        Add a member to a project.
        
        Args:
            db: Database session
            project_id: Project UUID
            member_data: Member data (user_id and role)
            
        Returns:
            ProjectMember: Created project member
            
        Raises:
            ValueError: If user is already a member
        """
        # Check if user is already a member
        existing = await db.execute(
            select(ProjectMember)
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == member_data.user_id
                )
            )
        )
        
        if existing.scalar_one_or_none() is not None:
            raise ValueError("User is already a member of this project")
        
        # Create new member
        member = ProjectMember(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role
        )
        
        db.add(member)
        await db.commit()
        await db.refresh(member)
        
        logger.info(f"Member added to project {project_id}: user {member_data.user_id} as {member_data.role}")
        return member
    
    @staticmethod
    async def list_members(
        db: AsyncSession,
        project_id: UUID
    ) -> List[ProjectMember]:
        """
        List all members of a project.
        
        Args:
            db: Database session
            project_id: Project UUID
            
        Returns:
            List[ProjectMember]: List of project members
        """
        result = await db.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .options(selectinload(ProjectMember.user))
            .order_by(ProjectMember.created_at)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_member_role(
        db: AsyncSession,
        project_id: UUID,
        user_id: UUID,
        role_data: ProjectMemberUpdate
    ) -> Optional[ProjectMember]:
        """
        Update a member's role in a project.
        
        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID
            role_data: New role data
            
        Returns:
            Optional[ProjectMember]: Updated member if found, None otherwise
        """
        result = await db.execute(
            select(ProjectMember)
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None:
            return None
        
        member.role = role_data.role
        await db.commit()
        await db.refresh(member)
        
        logger.info(f"Member role updated in project {project_id}: user {user_id} to {role_data.role}")
        return member
    
    @staticmethod
    async def remove_member(
        db: AsyncSession,
        project_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Remove a member from a project.
        
        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID
            
        Returns:
            bool: True if removed, False if not found
        """
        result = await db.execute(
            select(ProjectMember)
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None:
            return False
        
        await db.delete(member)
        await db.commit()
        
        logger.info(f"Member removed from project {project_id}: user {user_id}")
        return True

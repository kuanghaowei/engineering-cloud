"""Project Service"""

from uuid import UUID
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.logging_config import get_logger

logger = get_logger(__name__)


class ProjectService:
    """Service for managing project operations"""
    
    @staticmethod
    async def create_project(
        db: AsyncSession,
        project_data: ProjectCreate,
        creator: User
    ) -> Project:
        """
        Create a new project and assign creator as owner.
        
        Args:
            db: Database session
            project_data: Project creation data
            creator: User creating the project
            
        Returns:
            Project: Created project
        """
        # Create project
        project = Project(
            name=project_data.name,
            description=project_data.description,
            tenant_id=creator.tenant_id
        )
        
        db.add(project)
        await db.flush()  # Flush to get project.id
        
        # Add creator as owner (satisfies Property 4: Permission matrix initialization)
        member = ProjectMember(
            project_id=project.id,
            user_id=creator.id,
            role=ProjectRole.OWNER
        )
        
        db.add(member)
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Project created: {project.name} (ID: {project.id}) by user {creator.id}")
        return project
    
    @staticmethod
    async def get_project(
        db: AsyncSession,
        project_id: UUID
    ) -> Optional[Project]:
        """
        Get a project by ID.
        
        Args:
            db: Database session
            project_id: Project UUID
            
        Returns:
            Optional[Project]: Project if found, None otherwise
        """
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_projects(
        db: AsyncSession,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        """
        List all projects for a tenant with pagination.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Project]: List of projects
        """
        result = await db.execute(
            select(Project)
            .where(Project.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def list_user_projects(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        """
        List all projects where user is a member.
        
        Args:
            db: Database session
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Project]: List of projects
        """
        result = await db.execute(
            select(Project)
            .join(ProjectMember)
            .where(ProjectMember.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_project(
        db: AsyncSession,
        project_id: UUID,
        project_data: ProjectUpdate
    ) -> Optional[Project]:
        """
        Update a project.
        
        Args:
            db: Database session
            project_id: Project UUID
            project_data: Project update data
            
        Returns:
            Optional[Project]: Updated project if found, None otherwise
        """
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if project is None:
            return None
        
        # Update fields if provided
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Project updated: {project.name} (ID: {project.id})")
        return project
    
    @staticmethod
    async def delete_project(
        db: AsyncSession,
        project_id: UUID
    ) -> bool:
        """
        Delete a project.
        
        Args:
            db: Database session
            project_id: Project UUID
            
        Returns:
            bool: True if deleted, False if not found
        """
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if project is None:
            return False
        
        await db.delete(project)
        await db.commit()
        
        logger.info(f"Project deleted: {project.name} (ID: {project.id})")
        return True

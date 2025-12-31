"""Repository Service"""

from uuid import UUID
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository
from app.models.project import Project
from app.schemas.repository import RepositoryCreate, RepositoryUpdate
from app.logging_config import get_logger

logger = get_logger(__name__)


class RepositoryService:
    """Service for managing repository operations"""
    
    @staticmethod
    async def create_repository(
        db: AsyncSession,
        project_id: UUID,
        repository_data: RepositoryCreate
    ) -> Repository:
        """
        Create a new repository within a project.
        
        Args:
            db: Database session
            project_id: Project UUID
            repository_data: Repository creation data
            
        Returns:
            Repository: Created repository
        """
        repository = Repository(
            name=repository_data.name,
            description=repository_data.description,
            specialty=repository_data.specialty,
            project_id=project_id
        )
        
        db.add(repository)
        await db.commit()
        await db.refresh(repository)
        
        logger.info(f"Repository created: {repository.name} (ID: {repository.id}) in project {project_id}")
        return repository
    
    @staticmethod
    async def get_repository(
        db: AsyncSession,
        repository_id: UUID
    ) -> Optional[Repository]:
        """
        Get a repository by ID.
        
        Args:
            db: Database session
            repository_id: Repository UUID
            
        Returns:
            Optional[Repository]: Repository if found, None otherwise
        """
        result = await db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_repositories(
        db: AsyncSession,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Repository]:
        """
        List all repositories for a project with pagination.
        
        Args:
            db: Database session
            project_id: Project UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Repository]: List of repositories
        """
        result = await db.execute(
            select(Repository)
            .where(Repository.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .order_by(Repository.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_repository(
        db: AsyncSession,
        repository_id: UUID,
        repository_data: RepositoryUpdate
    ) -> Optional[Repository]:
        """
        Update a repository.
        
        Args:
            db: Database session
            repository_id: Repository UUID
            repository_data: Repository update data
            
        Returns:
            Optional[Repository]: Updated repository if found, None otherwise
        """
        result = await db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = result.scalar_one_or_none()
        
        if repository is None:
            return None
        
        # Update fields if provided
        if repository_data.name is not None:
            repository.name = repository_data.name
        if repository_data.description is not None:
            repository.description = repository_data.description
        if repository_data.specialty is not None:
            repository.specialty = repository_data.specialty
        
        await db.commit()
        await db.refresh(repository)
        
        logger.info(f"Repository updated: {repository.name} (ID: {repository.id})")
        return repository
    
    @staticmethod
    async def delete_repository(
        db: AsyncSession,
        repository_id: UUID
    ) -> bool:
        """
        Delete a repository.
        
        Args:
            db: Database session
            repository_id: Repository UUID
            
        Returns:
            bool: True if deleted, False if not found
        """
        result = await db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = result.scalar_one_or_none()
        
        if repository is None:
            return False
        
        await db.delete(repository)
        await db.commit()
        
        logger.info(f"Repository deleted: {repository.name} (ID: {repository.id})")
        return True

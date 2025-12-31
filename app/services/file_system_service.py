"""File System Service"""

from uuid import UUID
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_node import FileNode, NodeType
from app.models.repository import Repository
from app.schemas.file_node import FileNodeCreate, FileNodeUpdate, FileNodeMove
from app.logging_config import get_logger

logger = get_logger(__name__)


class FileSystemService:
    """Service for managing file system operations"""
    
    @staticmethod
    async def create_directory(
        db: AsyncSession,
        repository_id: UUID,
        directory_data: FileNodeCreate
    ) -> FileNode:
        """
        Create a new directory node.
        
        Args:
            db: Database session
            repository_id: Repository UUID
            directory_data: Directory creation data
            
        Returns:
            FileNode: Created directory node
            
        Raises:
            ValueError: If node_type is not DIRECTORY
        """
        if directory_data.node_type != NodeType.DIRECTORY:
            raise ValueError("Node type must be DIRECTORY for create_directory")
        
        directory = FileNode(
            name=directory_data.name,
            path=directory_data.path,
            node_type=NodeType.DIRECTORY,
            parent_id=directory_data.parent_id,
            repository_id=repository_id,
            current_version_id=None  # Directories don't have versions
        )
        
        db.add(directory)
        await db.commit()
        await db.refresh(directory)
        
        logger.info(f"Directory created: {directory.path} (ID: {directory.id}) in repository {repository_id}")
        return directory
    
    @staticmethod
    async def create_file(
        db: AsyncSession,
        repository_id: UUID,
        file_data: FileNodeCreate
    ) -> FileNode:
        """
        Create a new file node.
        
        Args:
            db: Database session
            repository_id: Repository UUID
            file_data: File creation data
            
        Returns:
            FileNode: Created file node
            
        Raises:
            ValueError: If node_type is not FILE
        """
        if file_data.node_type != NodeType.FILE:
            raise ValueError("Node type must be FILE for create_file")
        
        file_node = FileNode(
            name=file_data.name,
            path=file_data.path,
            node_type=NodeType.FILE,
            parent_id=file_data.parent_id,
            repository_id=repository_id,
            current_version_id=None  # Will be set when first version is created
        )
        
        db.add(file_node)
        await db.commit()
        await db.refresh(file_node)
        
        logger.info(f"File created: {file_node.path} (ID: {file_node.id}) in repository {repository_id}")
        return file_node
    
    @staticmethod
    async def get_file_node(
        db: AsyncSession,
        node_id: UUID
    ) -> Optional[FileNode]:
        """
        Get a file node by ID.
        
        Args:
            db: Database session
            node_id: FileNode UUID
            
        Returns:
            Optional[FileNode]: FileNode if found, None otherwise
        """
        result = await db.execute(
            select(FileNode).where(FileNode.id == node_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_file_node_by_path(
        db: AsyncSession,
        repository_id: UUID,
        path: str
    ) -> Optional[FileNode]:
        """
        Get a file node by path within a repository.
        
        Args:
            db: Database session
            repository_id: Repository UUID
            path: File path
            
        Returns:
            Optional[FileNode]: FileNode if found, None otherwise
        """
        result = await db.execute(
            select(FileNode).where(
                and_(
                    FileNode.repository_id == repository_id,
                    FileNode.path == path
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_children(
        db: AsyncSession,
        parent_id: Optional[UUID],
        repository_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[FileNode]:
        """
        List all children of a directory node.
        
        Args:
            db: Database session
            parent_id: Parent node UUID (None for root level)
            repository_id: Repository UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[FileNode]: List of child nodes
        """
        result = await db.execute(
            select(FileNode)
            .where(
                and_(
                    FileNode.parent_id == parent_id,
                    FileNode.repository_id == repository_id
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(FileNode.node_type.desc(), FileNode.name)  # Directories first, then files
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def list_repository_nodes(
        db: AsyncSession,
        repository_id: UUID,
        skip: int = 0,
        limit: int = 1000
    ) -> List[FileNode]:
        """
        List all nodes in a repository.
        
        Args:
            db: Database session
            repository_id: Repository UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[FileNode]: List of all nodes
        """
        result = await db.execute(
            select(FileNode)
            .where(FileNode.repository_id == repository_id)
            .offset(skip)
            .limit(limit)
            .order_by(FileNode.path)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def move_node(
        db: AsyncSession,
        node_id: UUID,
        move_data: FileNodeMove
    ) -> Optional[FileNode]:
        """
        Move a file node to a new location.
        
        This updates the node's path and parent_id.
        For directories, all children paths must also be updated.
        
        Args:
            db: Database session
            node_id: FileNode UUID
            move_data: Move operation data
            
        Returns:
            Optional[FileNode]: Updated node if found, None otherwise
        """
        result = await db.execute(
            select(FileNode).where(FileNode.id == node_id)
        )
        node = result.scalar_one_or_none()
        
        if node is None:
            return None
        
        old_path = node.path
        new_path = move_data.new_path
        
        # Update the node
        node.path = new_path
        if move_data.new_parent_id is not None:
            node.parent_id = move_data.new_parent_id
        
        # If it's a directory, update all children paths
        if node.node_type == NodeType.DIRECTORY:
            # Get all descendants
            result = await db.execute(
                select(FileNode).where(
                    and_(
                        FileNode.repository_id == node.repository_id,
                        FileNode.path.like(f"{old_path}/%")
                    )
                )
            )
            descendants = result.scalars().all()
            
            # Update each descendant's path
            for descendant in descendants:
                # Replace the old path prefix with the new one
                descendant.path = descendant.path.replace(old_path, new_path, 1)
        
        await db.commit()
        await db.refresh(node)
        
        logger.info(f"Node moved: {old_path} -> {new_path} (ID: {node.id})")
        return node
    
    @staticmethod
    async def update_node(
        db: AsyncSession,
        node_id: UUID,
        node_data: FileNodeUpdate
    ) -> Optional[FileNode]:
        """
        Update a file node's metadata.
        
        Args:
            db: Database session
            node_id: FileNode UUID
            node_data: Node update data
            
        Returns:
            Optional[FileNode]: Updated node if found, None otherwise
        """
        result = await db.execute(
            select(FileNode).where(FileNode.id == node_id)
        )
        node = result.scalar_one_or_none()
        
        if node is None:
            return None
        
        # Update fields if provided
        if node_data.name is not None:
            node.name = node_data.name
        if node_data.path is not None:
            node.path = node_data.path
        if node_data.parent_id is not None:
            node.parent_id = node_data.parent_id
        
        await db.commit()
        await db.refresh(node)
        
        logger.info(f"Node updated: {node.path} (ID: {node.id})")
        return node
    
    @staticmethod
    async def delete_node(
        db: AsyncSession,
        node_id: UUID
    ) -> bool:
        """
        Delete a file node.
        
        For directories, all children are also deleted (cascade).
        
        Args:
            db: Database session
            node_id: FileNode UUID
            
        Returns:
            bool: True if deleted, False if not found
        """
        result = await db.execute(
            select(FileNode).where(FileNode.id == node_id)
        )
        node = result.scalar_one_or_none()
        
        if node is None:
            return False
        
        await db.delete(node)
        await db.commit()
        
        logger.info(f"Node deleted: {node.path} (ID: {node.id})")
        return True
    
    @staticmethod
    async def validate_path(
        db: AsyncSession,
        repository_id: UUID,
        path: str,
        parent_id: Optional[UUID]
    ) -> bool:
        """
        Validate that a path is valid within a repository.
        
        Checks:
        - Path doesn't already exist
        - Parent exists if parent_id is provided
        - Path is consistent with parent path
        
        Args:
            db: Database session
            repository_id: Repository UUID
            path: Path to validate
            parent_id: Parent node UUID (if any)
            
        Returns:
            bool: True if path is valid, False otherwise
        """
        # Check if path already exists
        existing = await FileSystemService.get_file_node_by_path(db, repository_id, path)
        if existing is not None:
            logger.warning(f"Path already exists: {path}")
            return False
        
        # If parent_id is provided, validate parent exists and path is consistent
        if parent_id is not None:
            parent = await FileSystemService.get_file_node(db, parent_id)
            if parent is None:
                logger.warning(f"Parent node not found: {parent_id}")
                return False
            
            # Check that parent is a directory
            if parent.node_type != NodeType.DIRECTORY:
                logger.warning(f"Parent is not a directory: {parent_id}")
                return False
            
            # Check that path starts with parent path
            if not path.startswith(parent.path + '/'):
                logger.warning(f"Path {path} is not under parent path {parent.path}")
                return False
        
        return True

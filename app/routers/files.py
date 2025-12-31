"""File System Router"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.file_node import NodeType
from app.schemas.file_node import (
    FileNodeCreate,
    FileNodeUpdate,
    FileNodeMove,
    FileNodeResponse
)
from app.services.file_system_service import FileSystemService
from app.services.repository_service import RepositoryService
from app.services.project_service import ProjectService
from app.auth import get_current_active_user
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/files", tags=["Files"])


@router.post("", response_model=FileNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_file_node(
    repository_id: UUID = Query(..., description="Repository ID to create node in"),
    node_data: FileNodeCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new file or directory node.
    
    Args:
        repository_id: Repository UUID
        node_data: Node creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        FileNodeResponse: Created node information
        
    Raises:
        HTTPException: If repository not found, access denied, or validation fails
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
    
    # Validate path
    is_valid = await FileSystemService.validate_path(
        db,
        repository_id,
        node_data.path,
        node_data.parent_id
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path or path already exists"
        )
    
    # Create node based on type
    if node_data.node_type == NodeType.DIRECTORY:
        node = await FileSystemService.create_directory(db, repository_id, node_data)
    else:
        node = await FileSystemService.create_file(db, repository_id, node_data)
    
    return node


@router.get("/{node_id}", response_model=FileNodeResponse)
async def get_file_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a file node by ID.
    
    Args:
        node_id: FileNode UUID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        FileNodeResponse: Node information
        
    Raises:
        HTTPException: If node not found or access denied
    """
    node = await FileSystemService.get_file_node(db, node_id)
    
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File node with ID {node_id} not found"
        )
    
    # Check tenant isolation through repository -> project
    repository = await RepositoryService.get_repository(db, node.repository_id)
    if repository:
        project = await ProjectService.get_project(db, repository.project_id)
        if project and project.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: file node belongs to different tenant"
            )
    
    return node


@router.get("", response_model=List[FileNodeResponse])
async def list_file_nodes(
    repository_id: UUID = Query(..., description="Repository ID to list nodes from"),
    parent_id: Optional[UUID] = Query(None, description="Parent node ID (None for root level)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List file nodes in a repository.
    
    If parent_id is provided, lists children of that directory.
    If parent_id is None, lists root-level nodes.
    
    Args:
        repository_id: Repository UUID
        parent_id: Parent node UUID (None for root level)
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[FileNodeResponse]: List of file nodes
        
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
    
    # List children or all nodes
    if parent_id is not None:
        nodes = await FileSystemService.list_children(db, parent_id, repository_id, skip, limit)
    else:
        nodes = await FileSystemService.list_children(db, None, repository_id, skip, limit)
    
    return nodes


@router.put("/{node_id}", response_model=FileNodeResponse)
async def update_file_node(
    node_id: UUID,
    node_data: FileNodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a file node's metadata.
    
    Args:
        node_id: FileNode UUID
        node_data: Node update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        FileNodeResponse: Updated node information
        
    Raises:
        HTTPException: If node not found or access denied
    """
    # Check if node exists and belongs to user's tenant
    node = await FileSystemService.get_file_node(db, node_id)
    
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File node with ID {node_id} not found"
        )
    
    # Check tenant isolation through repository -> project
    repository = await RepositoryService.get_repository(db, node.repository_id)
    if repository:
        project = await ProjectService.get_project(db, repository.project_id)
        if project and project.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: file node belongs to different tenant"
            )
    
    updated_node = await FileSystemService.update_node(db, node_id, node_data)
    return updated_node


@router.post("/{node_id}/move", response_model=FileNodeResponse)
async def move_file_node(
    node_id: UUID,
    move_data: FileNodeMove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Move a file node to a new location.
    
    This updates the node's path and parent. For directories,
    all children paths are also updated.
    
    Args:
        node_id: FileNode UUID
        move_data: Move operation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        FileNodeResponse: Updated node information
        
    Raises:
        HTTPException: If node not found or access denied
    """
    # Check if node exists and belongs to user's tenant
    node = await FileSystemService.get_file_node(db, node_id)
    
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File node with ID {node_id} not found"
        )
    
    # Check tenant isolation through repository -> project
    repository = await RepositoryService.get_repository(db, node.repository_id)
    if repository:
        project = await ProjectService.get_project(db, repository.project_id)
        if project and project.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: file node belongs to different tenant"
            )
    
    # Validate new path
    is_valid = await FileSystemService.validate_path(
        db,
        node.repository_id,
        move_data.new_path,
        move_data.new_parent_id
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid new path or path already exists"
        )
    
    moved_node = await FileSystemService.move_node(db, node_id, move_data)
    return moved_node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a file node.
    
    For directories, all children are also deleted (cascade).
    
    Args:
        node_id: FileNode UUID
        db: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException: If node not found or access denied
    """
    # Check if node exists and belongs to user's tenant
    node = await FileSystemService.get_file_node(db, node_id)
    
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File node with ID {node_id} not found"
        )
    
    # Check tenant isolation through repository -> project
    repository = await RepositoryService.get_repository(db, node.repository_id)
    if repository:
        project = await ProjectService.get_project(db, repository.project_id)
        if project and project.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: file node belongs to different tenant"
            )
    
    await FileSystemService.delete_node(db, node_id)

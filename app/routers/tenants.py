"""Tenant Router"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services.tenant_service import TenantService
from app.auth import get_current_active_user
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/tenants", tags=["Tenants"])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new tenant.
    
    Args:
        tenant_data: Tenant creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Created tenant information
    """
    tenant = await TenantService.create_tenant(db, tenant_data)
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a tenant by ID.
    
    Args:
        tenant_id: Tenant UUID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Tenant information
        
    Raises:
        HTTPException: If tenant not found
    """
    tenant = await TenantService.get_tenant(db, tenant_id)
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found"
        )
    
    return tenant


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all tenants with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[TenantResponse]: List of tenants
    """
    tenants = await TenantService.list_tenants(db, skip, limit)
    return tenants


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a tenant.
    
    Args:
        tenant_id: Tenant UUID
        tenant_data: Tenant update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant information
        
    Raises:
        HTTPException: If tenant not found
    """
    tenant = await TenantService.update_tenant(db, tenant_id, tenant_data)
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found"
        )
    
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a tenant.
    
    Args:
        tenant_id: Tenant UUID
        db: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException: If tenant not found
    """
    deleted = await TenantService.delete_tenant(db, tenant_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found"
        )

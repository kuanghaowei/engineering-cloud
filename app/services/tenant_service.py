"""Tenant Service"""

from uuid import UUID
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantType
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.logging_config import get_logger

logger = get_logger(__name__)


class TenantService:
    """Service for managing tenant operations"""
    
    @staticmethod
    async def create_tenant(
        db: AsyncSession,
        tenant_data: TenantCreate
    ) -> Tenant:
        """
        Create a new tenant.
        
        Args:
            db: Database session
            tenant_data: Tenant creation data
            
        Returns:
            Tenant: Created tenant
        """
        tenant = Tenant(
            name=tenant_data.name,
            tenant_type=tenant_data.tenant_type
        )
        
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"Tenant created: {tenant.name} (ID: {tenant.id})")
        return tenant
    
    @staticmethod
    async def get_tenant(
        db: AsyncSession,
        tenant_id: UUID
    ) -> Optional[Tenant]:
        """
        Get a tenant by ID.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            
        Returns:
            Optional[Tenant]: Tenant if found, None otherwise
        """
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_tenants(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tenant]:
        """
        List all tenants with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Tenant]: List of tenants
        """
        result = await db.execute(
            select(Tenant)
            .offset(skip)
            .limit(limit)
            .order_by(Tenant.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_tenant(
        db: AsyncSession,
        tenant_id: UUID,
        tenant_data: TenantUpdate
    ) -> Optional[Tenant]:
        """
        Update a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            tenant_data: Tenant update data
            
        Returns:
            Optional[Tenant]: Updated tenant if found, None otherwise
        """
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if tenant is None:
            return None
        
        # Update fields if provided
        if tenant_data.name is not None:
            tenant.name = tenant_data.name
        if tenant_data.tenant_type is not None:
            tenant.tenant_type = tenant_data.tenant_type
        
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"Tenant updated: {tenant.name} (ID: {tenant.id})")
        return tenant
    
    @staticmethod
    async def delete_tenant(
        db: AsyncSession,
        tenant_id: UUID
    ) -> bool:
        """
        Delete a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            
        Returns:
            bool: True if deleted, False if not found
        """
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if tenant is None:
            return False
        
        await db.delete(tenant)
        await db.commit()
        
        logger.info(f"Tenant deleted: {tenant.name} (ID: {tenant.id})")
        return True

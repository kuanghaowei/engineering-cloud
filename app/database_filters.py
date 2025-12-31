"""Database Query Filters for Tenant Isolation"""

from typing import Type, TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import DeclarativeMeta

from app.middleware.tenant_context import TenantContext
from app.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=DeclarativeMeta)


def apply_tenant_filter(query: Select[tuple[T]], model: Type[T]) -> Select[tuple[T]]:
    """
    Apply tenant filter to a SQLAlchemy query.
    
    This function automatically adds a WHERE clause to filter by tenant_id
    if the model has a tenant_id column and a tenant context is set.
    
    Args:
        query: SQLAlchemy select query
        model: SQLAlchemy model class
        
    Returns:
        Select: Query with tenant filter applied
    """
    tenant_id = TenantContext.get_tenant_id()
    
    # Only apply filter if tenant context is set and model has tenant_id
    if tenant_id and hasattr(model, 'tenant_id'):
        logger.debug(f"Applying tenant filter: {tenant_id} to {model.__name__}")
        return query.where(model.tenant_id == tenant_id)
    
    return query


def get_tenant_filtered_query(model: Type[T]) -> Select[tuple[T]]:
    """
    Create a tenant-filtered query for a model.
    
    This is a convenience function that creates a select query and
    automatically applies the tenant filter.
    
    Args:
        model: SQLAlchemy model class
        
    Returns:
        Select: Tenant-filtered select query
    """
    query = select(model)
    return apply_tenant_filter(query, model)


class TenantFilterMixin:
    """
    Mixin class to add tenant filtering capabilities to models.
    
    Models that inherit from this mixin will have helper methods
    for creating tenant-filtered queries.
    """
    
    @classmethod
    def tenant_query(cls) -> Select:
        """
        Create a tenant-filtered query for this model.
        
        Returns:
            Select: Tenant-filtered select query
        """
        return get_tenant_filtered_query(cls)

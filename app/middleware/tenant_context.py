"""Tenant Context Middleware"""

from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from app.logging_config import get_logger

logger = get_logger(__name__)

# Context variable to store tenant ID for the current request
_tenant_context: ContextVar[Optional[UUID]] = ContextVar('tenant_context', default=None)


class TenantContext:
    """
    Tenant context manager for request-level tenant isolation.
    
    This class provides methods to get and set the current tenant ID
    for the active request context.
    """
    
    @staticmethod
    def get_tenant_id() -> Optional[UUID]:
        """
        Get the current tenant ID from context.
        
        Returns:
            Optional[UUID]: Current tenant ID or None if not set
        """
        return _tenant_context.get()
    
    @staticmethod
    def set_tenant_id(tenant_id: UUID) -> None:
        """
        Set the tenant ID in the current context.
        
        Args:
            tenant_id: Tenant ID to set
        """
        _tenant_context.set(tenant_id)
        logger.debug(f"Tenant context set: {tenant_id}")
    
    @staticmethod
    def clear() -> None:
        """Clear the tenant context."""
        _tenant_context.set(None)


def get_tenant_id() -> Optional[UUID]:
    """
    Dependency function to get the current tenant ID.
    
    Returns:
        Optional[UUID]: Current tenant ID from context
    """
    return TenantContext.get_tenant_id()

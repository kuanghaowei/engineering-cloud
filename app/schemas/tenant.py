"""Tenant Schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.tenant import TenantType


class TenantCreate(BaseModel):
    """Schema for creating a tenant"""
    name: str = Field(..., min_length=1, max_length=255)
    tenant_type: TenantType


class TenantUpdate(BaseModel):
    """Schema for updating a tenant"""
    name: str | None = Field(None, min_length=1, max_length=255)
    tenant_type: TenantType | None = None


class TenantResponse(BaseModel):
    """Schema for tenant response"""
    id: UUID
    name: str
    tenant_type: TenantType
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }

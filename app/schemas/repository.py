"""Repository Schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class RepositoryCreate(BaseModel):
    """Schema for creating a repository"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    specialty: Optional[str] = Field(None, max_length=100)


class RepositoryUpdate(BaseModel):
    """Schema for updating a repository"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    specialty: Optional[str] = Field(None, max_length=100)


class RepositoryResponse(BaseModel):
    """Schema for repository response"""
    id: UUID
    name: str
    description: Optional[str]
    specialty: Optional[str]
    project_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }

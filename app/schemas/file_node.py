"""FileNode Schemas"""

from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.file_node import NodeType


class FileNodeCreate(BaseModel):
    """Schema for creating a file node"""
    name: str = Field(..., min_length=1, max_length=255)
    path: str = Field(..., min_length=1, max_length=2000)
    node_type: NodeType
    parent_id: Optional[UUID] = None
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path format"""
        if not v.startswith('/'):
            raise ValueError('Path must start with /')
        if v.endswith('/') and v != '/':
            raise ValueError('Path must not end with / (except root)')
        return v


class FileNodeUpdate(BaseModel):
    """Schema for updating a file node"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    path: Optional[str] = Field(None, min_length=1, max_length=2000)
    parent_id: Optional[UUID] = None
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate path format"""
        if v is not None:
            if not v.startswith('/'):
                raise ValueError('Path must start with /')
            if v.endswith('/') and v != '/':
                raise ValueError('Path must not end with / (except root)')
        return v


class FileNodeMove(BaseModel):
    """Schema for moving a file node"""
    new_path: str = Field(..., min_length=1, max_length=2000)
    new_parent_id: Optional[UUID] = None
    
    @field_validator('new_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path format"""
        if not v.startswith('/'):
            raise ValueError('Path must start with /')
        if v.endswith('/') and v != '/':
            raise ValueError('Path must not end with / (except root)')
        return v


class FileNodeResponse(BaseModel):
    """Schema for file node response"""
    id: UUID
    name: str
    path: str
    node_type: NodeType
    parent_id: Optional[UUID]
    repository_id: UUID
    current_version_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }

"""Permission Schemas"""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.project import ProjectRole
from typing import Optional


class ProjectMemberAdd(BaseModel):
    """Schema for adding a member to a project"""
    user_id: UUID
    role: ProjectRole


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a project member's role"""
    role: ProjectRole


class ProjectMemberResponse(BaseModel):
    """Schema for project member response"""
    id: UUID
    project_id: UUID
    user_id: UUID
    role: ProjectRole
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class UserWithRole(BaseModel):
    """Schema for user with their project role"""
    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    role: ProjectRole
    
    model_config = {
        "from_attributes": True
    }

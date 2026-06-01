"""Pydantic schemas (DTOs) for user management API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreateSchema(BaseModel):
    """Schema for creating a new user."""

    username: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    role: str = Field(default="user")
    avatar_url: Optional[str] = None
    badge_number: Optional[str] = None


class UserUpdateSchema(BaseModel):
    """Schema for updating an existing user."""

    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    badge_number: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponseSchema(BaseModel):
    """Schema for user API responses."""

    id: int
    username: str
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    badge_number: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

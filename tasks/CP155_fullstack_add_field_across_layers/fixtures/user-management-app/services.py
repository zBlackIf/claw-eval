"""User service — business logic for account management."""
from __future__ import annotations

from typing import Optional

from models import User, db
from schemas import UserCreateSchema, UserUpdateSchema


class UserService:
    """Handles user CRUD operations."""

    @staticmethod
    def create_user(data: UserCreateSchema) -> User:
        """Create a new user account."""
        user = User(
            username=data.username,
            display_name=data.display_name,
            email=data.email,
            phone=data.phone,
            department=data.department,
            role=data.role,
            avatar_url=data.avatar_url,
            badge_number=data.badge_number,
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update_user(user_id: int, data: UserUpdateSchema) -> Optional[User]:
        """Update an existing user account."""
        user = User.query.get(user_id)
        if not user:
            return None

        if data.display_name is not None:
            user.display_name = data.display_name
        if data.email is not None:
            user.email = data.email
        if data.phone is not None:
            user.phone = data.phone
        if data.department is not None:
            user.department = data.department
        if data.role is not None:
            user.role = data.role
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url
        if data.badge_number is not None:
            user.badge_number = data.badge_number
        if data.is_active is not None:
            user.is_active = data.is_active

        db.session.commit()
        return user

    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return User.query.get(user_id)

    @staticmethod
    def list_users(active_only: bool = False) -> list[User]:
        """List all users, optionally filtering by active status."""
        query = User.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(User.id).all()

    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Soft-delete a user by setting is_active=False."""
        user = User.query.get(user_id)
        if not user:
            return False
        user.is_active = False
        db.session.commit()
        return True

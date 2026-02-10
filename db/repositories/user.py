"""
Repository for user management (authentication, CRUD).
"""

import hashlib
import secrets
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from db.repositories.base import BaseRepository


VALID_ROLES = ("guest", "web", "user", "admin")


def generate_salt() -> str:
    """Generate a random 32-byte hex salt."""
    return secrets.token_hex(32)


def hash_password(password: str, salt: str) -> str:
    """Hash password with salt using SHA-256."""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """Verify password against stored hash."""
    return hash_password(password, salt) == password_hash


class UserRepository(BaseRepository[User]):
    """Repository for user CRUD and authentication."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username, User.is_active == True)
        )
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user by username and password. Returns user dict or None."""
        user = await self.get_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.salt, user.password_hash):
            return None

        # Update last_login
        user.last_login = datetime.utcnow()
        await self.session.commit()

        return user.to_dict()

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        display_name: Optional[str] = None,
    ) -> dict:
        """Create a new user. Returns user dict."""
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

        salt = generate_salt()
        pw_hash = hash_password(password, salt)

        user = User(
            username=username,
            password_hash=pw_hash,
            salt=salt,
            role=role,
            display_name=display_name or username,
            is_active=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user.to_dict()

    async def update_password(self, user_id: int, new_password: str) -> bool:
        """Update user's password."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        salt = generate_salt()
        user.salt = salt
        user.password_hash = hash_password(new_password, salt)
        user.updated = datetime.utcnow()
        await self.session.commit()
        return True

    async def update_profile(
        self, user_id: int, display_name: Optional[str] = None
    ) -> Optional[dict]:
        """Update user profile fields."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if display_name is not None:
            user.display_name = display_name
        user.updated = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(user)
        return user.to_dict()

    async def set_role(self, user_id: int, role: str) -> bool:
        """Change user's role."""
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.role = role
        user.updated = datetime.utcnow()
        await self.session.commit()
        return True

    async def set_active(self, user_id: int, active: bool) -> bool:
        """Enable or disable user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.is_active = active
        user.updated = datetime.utcnow()
        await self.session.commit()
        return True

    async def list_users(self, include_inactive: bool = False) -> List[dict]:
        """List all users."""
        query = select(User).order_by(User.created)
        if not include_inactive:
            query = query.where(User.is_active == True)

        result = await self.session.execute(query)
        users = result.scalars().all()
        return [u.to_dict() for u in users]

    async def delete_user(self, user_id: int) -> bool:
        """Delete user by ID."""
        return await self.delete_by_id(user_id)

    async def get_user_count(self) -> int:
        """Get total number of active users."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.is_active == True)
        )
        return result.scalar() or 0

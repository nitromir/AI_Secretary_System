"""
Authentication Manager for Admin Panel

Multi-user JWT-based authentication with DB-backed users and role-based access.
Roles: guest, user, admin.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("ADMIN_JWT_EXPIRATION_HOURS", "24"))

# Legacy env-var credentials (fallback when users table is empty)
_LEGACY_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
_LEGACY_PASSWORD_HASH: str = os.getenv("ADMIN_PASSWORD_HASH", "") or ""
if not _LEGACY_PASSWORD_HASH:
    _LEGACY_PASSWORD_HASH = hashlib.sha256(b"admin").hexdigest()


# ============== Pydantic Models ==============


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None


class TokenPayload(BaseModel):
    sub: str  # username
    user_id: int  # database user id
    role: str
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp


class User(BaseModel):
    id: int
    username: str
    role: str


# ============== Security ==============

security = HTTPBearer(auto_error=False)


# ============== Password Helpers ==============


def hash_password(password: str, salt: str = "") -> str:
    """Hash a password. If salt provided, uses salted hash (new system).
    If no salt, uses plain SHA-256 (legacy compat)."""
    if salt:
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against legacy unsalted hash."""
    return hash_password(password) == password_hash


# ============== Token Management ==============


def create_access_token(username: str, role: str = "admin", user_id: int = 0) -> tuple[str, int]:
    """Create a JWT access token.

    Returns:
        tuple: (token, expires_in_seconds)
    """
    now = datetime.utcnow()
    expires = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    expires_in = int((expires - now).total_seconds())

    payload = {
        "sub": username,
        "user_id": user_id,
        "role": role,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # Backward compat: old tokens may not have user_id
        if "user_id" not in payload:
            payload["user_id"] = 0
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


# ============== Authentication ==============


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user against DB. Falls back to env-var admin if no DB users."""
    try:
        from db.integration import async_user_manager

        user_data = await async_user_manager.authenticate(username, password)
        if user_data:
            return User(
                id=user_data["id"],
                username=user_data["username"],
                role=user_data["role"],
            )

        # If DB auth failed, check if DB has any users at all
        user_count = await async_user_manager.get_user_count()
        if user_count > 0:
            # DB has users, this is a real auth failure
            return None

    except Exception as e:
        logger.warning(f"DB auth failed, trying legacy: {e}")

    # Fallback: legacy env-var admin (when no users in DB or DB unavailable)
    if username == _LEGACY_USERNAME and verify_password(password, _LEGACY_PASSWORD_HASH):
        return User(id=0, username=username, role="admin")

    return None


# ============== FastAPI Dependencies ==============


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Dependency to get the current authenticated user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_payload = decode_token(credentials.credentials)
    if token_payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(id=token_payload.user_id, username=token_payload.sub, role=token_payload.role)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Dependency to get the current user if authenticated, None otherwise."""
    if credentials is None:
        return None

    token_payload = decode_token(credentials.credentials)
    if token_payload is None:
        return None

    return User(id=token_payload.user_id, username=token_payload.sub, role=token_payload.role)


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_not_guest(user: User = Depends(get_current_user)) -> User:
    """Dependency to block guest from write operations. Allows user and admin."""
    if user.role == "guest":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest accounts cannot perform this action",
        )
    return user


def verify_ownership(user: User, record_owner_id: Optional[int]) -> None:
    """Raise 404 if user doesn't own the record (admin bypasses)."""
    if user.role == "admin":
        return
    if record_owner_id is not None and record_owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


# ============== Status ==============

AUTH_ENABLED = os.getenv("ADMIN_AUTH_ENABLED", "true").lower() in ("true", "1", "yes")


def get_auth_status() -> Dict:
    """Get current auth configuration status."""
    return {
        "enabled": AUTH_ENABLED,
        "jwt_expiration_hours": JWT_EXPIRATION_HOURS,
    }

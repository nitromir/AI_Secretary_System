# app/routers/auth.py
"""Authentication router - login, user info, auth status, profile management."""

import os

from fastapi import APIRouter, Depends, HTTPException, Request

from app.rate_limiter import RATE_LIMIT_AUTH, limiter
from auth_manager import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UpdateProfileRequest,
    User,
    authenticate_user,
    create_access_token,
    get_auth_status,
    get_current_user,
)
from db.integration import async_audit_logger, async_user_manager


router = APIRouter(prefix="/admin/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit(RATE_LIMIT_AUTH)
async def admin_login(request: Request, login_request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = await authenticate_user(login_request.username, login_request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token, expires_in = create_access_token(user.username, user.role, user.id)

    # Audit log
    await async_audit_logger.log(
        action="login", resource="auth", user_id=user.username, details={"role": user.role}
    )

    return LoginResponse(access_token=token, token_type="bearer", expires_in=expires_in)


@router.get("/me")
async def admin_get_current_user(user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    deployment_mode = os.getenv("DEPLOYMENT_MODE", "full").lower()
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "deployment_mode": deployment_mode,
    }


@router.get("/profile")
async def admin_get_profile(user: User = Depends(get_current_user)):
    """Get full user profile."""
    user_data = await async_user_manager.get_by_id(user.id)
    if not user_data:
        return {"id": user.id, "username": user.username, "role": user.role}
    return {
        "id": user_data["id"],
        "username": user_data["username"],
        "role": user_data["role"],
        "display_name": user_data.get("display_name"),
        "created": user_data.get("created"),
        "last_login": user_data.get("last_login"),
    }


@router.put("/profile")
async def admin_update_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_user),
):
    """Update user profile (display name)."""
    if user.role == "guest":
        raise HTTPException(status_code=403, detail="Guest cannot update profile")

    result = await async_user_manager.update_profile(user.id, display_name=request.display_name)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    await async_audit_logger.log(action="update", resource="profile", user_id=user.username)
    return result


@router.post("/change-password")
async def admin_change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
):
    """Change current user's password."""
    if user.role == "guest":
        raise HTTPException(status_code=403, detail="Guest cannot change password")

    # Verify old password
    auth_result = await authenticate_user(user.username, request.old_password)
    if not auth_result:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Update password
    success = await async_user_manager.update_password(user.id, request.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update password")

    await async_audit_logger.log(action="update", resource="password", user_id=user.username)
    return {"message": "Password updated successfully"}


@router.get("/status")
async def admin_auth_status():
    """Get authentication configuration status."""
    return get_auth_status()

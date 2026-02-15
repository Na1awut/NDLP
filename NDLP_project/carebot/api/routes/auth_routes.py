"""
Auth Routes — FastAPI endpoints for authentication

Endpoints:
  POST /auth/register        — Register with username + password
  POST /auth/login            — Login with username + password
  POST /auth/google           — Login with Google ID token
  GET  /auth/me               — Get current user profile
  POST /auth/link-platform    — Link a platform ID to account
  POST /auth/guest            — Create a guest session
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import APIRouter, HTTPException, Depends, status

from models.auth_models import (
    RegisterRequest,
    LoginRequest,
    GoogleLoginRequest,
    LinkPlatformRequest,
    GuestSessionRequest,
    AuthResponse,
    GuestResponse,
    UserProfile,
)
from services.auth_service import (
    register_user,
    login_user,
    google_login,
    create_jwt,
    create_guest_id,
    GUEST_EXPIRE_HOURS,
)
from api.middleware.auth_middleware import require_auth, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

# Will be injected by main.py
memory_store = None


# ──────────────────────────────────────────────
# Register
# ──────────────────────────────────────────────
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new account with username + password"""
    if not memory_store:
        raise HTTPException(status_code=500, detail="Services not initialized")

    try:
        user_data = await register_user(
            memory_store,
            username=request.username,
            password=request.password,
            display_name=request.display_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token, expires_in = create_jwt(
        user_id=user_data["user_id"],
        username=user_data["username"],
    )

    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserProfile(
            user_id=user_data["user_id"],
            username=user_data["username"],
            display_name=user_data.get("display_name"),
            auth_provider=user_data.get("auth_provider", "local"),
            platforms=user_data.get("platforms", {}),
            created_at=user_data.get("created_at", ""),
        ),
    )


# ──────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────
@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with username + password"""
    if not memory_store:
        raise HTTPException(status_code=500, detail="Services not initialized")

    try:
        user_data = await login_user(
            memory_store,
            username=request.username,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    token, expires_in = create_jwt(
        user_id=user_data["user_id"],
        username=user_data["username"],
    )

    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserProfile(
            user_id=user_data["user_id"],
            username=user_data["username"],
            display_name=user_data.get("display_name"),
            auth_provider=user_data.get("auth_provider", "local"),
            platforms=user_data.get("platforms", {}),
            created_at=user_data.get("created_at", ""),
        ),
    )


# ──────────────────────────────────────────────
# Google OAuth
# ──────────────────────────────────────────────
@router.post("/google", response_model=AuthResponse)
async def google_oauth(request: GoogleLoginRequest):
    """Login or register with Google ID token"""
    if not memory_store:
        raise HTTPException(status_code=500, detail="Services not initialized")

    try:
        user_data = await google_login(memory_store, request.id_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token, expires_in = create_jwt(
        user_id=user_data["user_id"],
        username=user_data.get("username"),
    )

    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserProfile(
            user_id=user_data["user_id"],
            username=user_data.get("username"),
            display_name=user_data.get("display_name"),
            auth_provider=user_data.get("auth_provider", "google"),
            platforms=user_data.get("platforms", {}),
            created_at=user_data.get("created_at", ""),
        ),
    )


# ──────────────────────────────────────────────
# Profile
# ──────────────────────────────────────────────
@router.get("/me", response_model=UserProfile)
async def get_me(user: UserProfile = Depends(require_auth)):
    """Get current user profile (requires login)"""
    if not memory_store:
        raise HTTPException(status_code=500, detail="Services not initialized")

    user_data = await memory_store.get_user(user.user_id)
    if not user_data:
        # Return basic info from JWT
        return user

    return UserProfile(
        user_id=user_data["user_id"],
        username=user_data.get("username"),
        display_name=user_data.get("display_name"),
        auth_provider=user_data.get("auth_provider", "local"),
        platforms=user_data.get("platforms", {}),
        created_at=user_data.get("created_at", ""),
    )


# ──────────────────────────────────────────────
# Link Platform
# ──────────────────────────────────────────────
@router.post("/link-platform")
async def link_platform(
    request: LinkPlatformRequest,
    user: UserProfile = Depends(require_auth),
):
    """Link a LINE/Discord ID to your account for cross-platform chat"""
    if not memory_store:
        raise HTTPException(status_code=500, detail="Services not initialized")

    if user.is_guest:
        raise HTTPException(
            status_code=400,
            detail="Guest accounts cannot link platforms — กรุณาสมัครสมาชิกก่อน",
        )

    await memory_store.link_platforms(user.user_id, request.platform, request.platform_id)

    return {
        "message": f"Linked {request.platform} to your account",
        "user_id": user.user_id,
        "platform": request.platform,
    }


# ──────────────────────────────────────────────
# Guest Session
# ──────────────────────────────────────────────
@router.post("/guest", response_model=GuestResponse)
async def create_guest(request: GuestSessionRequest):
    """Create a temporary guest session (no login required)"""
    guest_id = create_guest_id(request.platform)
    expires_in = GUEST_EXPIRE_HOURS * 3600

    return GuestResponse(
        guest_id=guest_id,
        expires_in=expires_in,
    )

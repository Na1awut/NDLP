"""
Auth Models — Pydantic schemas for authentication system
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ──────────────────────────────────────────────
# Request Models
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """POST /auth/register"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=6, max_length=128, description="Password")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")


class LoginRequest(BaseModel):
    """POST /auth/login"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class GoogleLoginRequest(BaseModel):
    """POST /auth/google"""
    id_token: str = Field(..., description="Google ID token from frontend")


class LinkPlatformRequest(BaseModel):
    """POST /auth/link-platform"""
    platform: str = Field(..., description="Platform name: line | discord | web")
    platform_id: str = Field(..., description="Platform-specific user ID")


class GuestSessionRequest(BaseModel):
    """POST /auth/guest"""
    platform: str = Field("web", description="Platform: line | discord | web")


# ──────────────────────────────────────────────
# Response Models
# ──────────────────────────────────────────────

class UserProfile(BaseModel):
    """User profile data"""
    user_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    auth_provider: str = "local"  # local | google
    platforms: dict[str, str] = Field(default_factory=dict)
    is_guest: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AuthResponse(BaseModel):
    """Auth success response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiry in seconds")
    user: UserProfile


class GuestResponse(BaseModel):
    """Guest session response"""
    guest_id: str
    expires_in: int = Field(description="Session expiry in seconds")
    message: str = "Guest session created — ใช้งานได้เลย แต่ประวัติจะไม่ข้าม platform"

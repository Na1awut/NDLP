"""
Auth Middleware — FastAPI dependencies for authentication

Provides:
  - get_current_user: Optional auth (returns None for guests)
  - require_auth: Mandatory auth (raises 401 if no token)
"""
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import decode_jwt
from models.auth_models import UserProfile

# Optional bearer token — won't fail if no token is provided
optional_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
) -> Optional[UserProfile]:
    """
    Extract user from JWT token if present.
    Returns None if no token (guest mode).
    """
    if not credentials:
        return None

    payload = decode_jwt(credentials.credentials)
    if not payload:
        return None

    return UserProfile(
        user_id=payload["sub"],
        username=payload.get("username"),
        is_guest=payload.get("is_guest", False),
    )


async def require_auth(
    user: Optional[UserProfile] = Depends(get_current_user),
) -> UserProfile:
    """
    Require a valid JWT token. Raises 401 if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required — กรุณา login ก่อน",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

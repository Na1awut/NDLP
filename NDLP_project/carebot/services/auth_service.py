"""
Auth Service — Registration, login, JWT, Google OAuth, guest sessions

Uses:
  - passlib + bcrypt for password hashing
  - PyJWT for token generation/validation
  - google-auth for Google ID token verification (optional)
"""
import os
import uuid
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "carebot-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))
GUEST_EXPIRE_HOURS = 24


# ──────────────────────────────────────────────
# Password Hashing (using bcrypt directly)
# ──────────────────────────────────────────────
def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ──────────────────────────────────────────────
# JWT Token
# ──────────────────────────────────────────────
def create_jwt(
    user_id: str,
    username: Optional[str] = None,
    is_guest: bool = False,
    expire_hours: Optional[int] = None,
) -> tuple[str, int]:
    """
    Create JWT token.
    Returns (token_string, expires_in_seconds)
    """
    hours = expire_hours or (GUEST_EXPIRE_HOURS if is_guest else JWT_EXPIRE_HOURS)
    expires_in = hours * 3600
    expire = datetime.now(timezone.utc) + timedelta(hours=hours)

    payload = {
        "sub": user_id,
        "username": username,
        "is_guest": is_guest,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_jwt(token: str) -> Optional[dict]:
    """
    Decode and validate JWT token.
    Returns payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("[Auth] Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"[Auth] Invalid token: {e}")
        return None


# ──────────────────────────────────────────────
# User Registration
# ──────────────────────────────────────────────
async def register_user(
    memory_store, username: str, password: str, display_name: Optional[str] = None
) -> dict:
    """
    Register a new user with username + password.
    Returns user_data dict.
    Raises ValueError if username already exists.
    """
    # Check if username already exists
    existing = await memory_store.find_user_by_username(username)
    if existing:
        raise ValueError(f"Username '{username}' already exists")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_data = {
        "id": user_id,
        "user_id": user_id,
        "username": username,
        "password_hash": hash_password(password),
        "display_name": display_name or username,
        "auth_provider": "local",
        "platforms": {},
        "is_guest": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    await memory_store.create_user(user_data)
    return user_data


# ──────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────
async def login_user(memory_store, username: str, password: str) -> dict:
    """
    Authenticate user with username + password.
    Returns user_data dict.
    Raises ValueError if credentials invalid.
    """
    user = await memory_store.find_user_by_username(username)
    if not user:
        raise ValueError("Invalid username or password")

    if not verify_password(password, user.get("password_hash", "")):
        raise ValueError("Invalid username or password")

    # Update last login
    user["last_login"] = datetime.now().isoformat()
    await memory_store.save_user(user["user_id"], user)

    return user


# ──────────────────────────────────────────────
# Google OAuth
# ──────────────────────────────────────────────
async def google_login(memory_store, id_token_str: str) -> dict:
    """
    Verify Google ID token and find/create user.
    Returns user_data dict.
    Raises ValueError if token is invalid or Google auth is not configured.
    """
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not google_client_id:
        raise ValueError("Google OAuth is not configured on this server")

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            google_client_id,
        )
    except Exception as e:
        raise ValueError(f"Invalid Google token: {e}")

    google_id = idinfo["sub"]
    email = idinfo.get("email", "")
    name = idinfo.get("name", email)

    # Find existing user by Google ID
    user = await memory_store.find_user_by_google_id(google_id)

    if not user:
        # Create new user from Google account
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "id": user_id,
            "user_id": user_id,
            "username": email,
            "google_id": google_id,
            "display_name": name,
            "auth_provider": "google",
            "platforms": {},
            "is_guest": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        await memory_store.create_user(user)
    else:
        # Update last login
        user["last_login"] = datetime.now().isoformat()
        await memory_store.save_user(user["user_id"], user)

    return user


# ──────────────────────────────────────────────
# Guest Session
# ──────────────────────────────────────────────
def create_guest_id(platform: str = "web") -> str:
    """Create a guest session ID (no persistence across platforms)"""
    return f"guest_{platform}_{uuid.uuid4().hex[:8]}"

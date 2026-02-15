"""
Test: Auth System — Registration, Login, JWT, Guest

Tests the auth service and auth routes independently (no LLM needed).
Uses in-memory store.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.auth_service import (
    hash_password,
    verify_password,
    create_jwt,
    decode_jwt,
    register_user,
    login_user,
    create_guest_id,
)
from services.memory_store import InMemoryStore


# ──────────────────────────────────────────────
# Password Hashing
# ──────────────────────────────────────────────
class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "secretpass123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt generates different salts


# ──────────────────────────────────────────────
# JWT Token
# ──────────────────────────────────────────────
class TestJWT:
    def test_create_and_decode(self):
        token, expires_in = create_jwt(user_id="user_abc", username="testuser")
        assert isinstance(token, str)
        assert expires_in > 0

        payload = decode_jwt(token)
        assert payload is not None
        assert payload["sub"] == "user_abc"
        assert payload["username"] == "testuser"
        assert payload["is_guest"] is False

    def test_guest_token(self):
        token, expires_in = create_jwt(user_id="guest_web_123", is_guest=True)
        payload = decode_jwt(token)
        assert payload["is_guest"] is True
        assert expires_in == 24 * 3600  # 24 hours for guest

    def test_invalid_token_returns_none(self):
        assert decode_jwt("totally.invalid.token") is None

    def test_empty_token_returns_none(self):
        assert decode_jwt("") is None


# ──────────────────────────────────────────────
# User Registration
# ──────────────────────────────────────────────
class TestRegistration:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.mark.asyncio
    async def test_register_success(self, store):
        user = await register_user(store, "newuser", "password123", "New User")
        assert user["username"] == "newuser"
        assert user["display_name"] == "New User"
        assert "password_hash" in user
        assert user["password_hash"] != "password123"
        assert user["auth_provider"] == "local"
        assert user["is_guest"] is False

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, store):
        await register_user(store, "dupeuser", "pass1")
        with pytest.raises(ValueError, match="already exists"):
            await register_user(store, "dupeuser", "pass2")

    @pytest.mark.asyncio
    async def test_register_default_display_name(self, store):
        user = await register_user(store, "noname", "pass123")
        assert user["display_name"] == "noname"


# ──────────────────────────────────────────────
# User Login
# ──────────────────────────────────────────────
class TestLogin:
    @pytest.fixture
    async def store_with_user(self):
        store = InMemoryStore()
        await register_user(store, "logintest", "mypassword")
        return store

    @pytest.mark.asyncio
    async def test_login_success(self, store_with_user):
        store = await store_with_user
        user = await login_user(store, "logintest", "mypassword")
        assert user["username"] == "logintest"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, store_with_user):
        store = await store_with_user
        with pytest.raises(ValueError, match="Invalid"):
            await login_user(store, "logintest", "wrongpassword")

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self):
        store = InMemoryStore()
        with pytest.raises(ValueError, match="Invalid"):
            await login_user(store, "noone", "whatever")


# ──────────────────────────────────────────────
# Guest Session
# ──────────────────────────────────────────────
class TestGuest:
    def test_guest_id_format(self):
        gid = create_guest_id("web")
        assert gid.startswith("guest_web_")
        assert len(gid) > 10

    def test_guest_ids_unique(self):
        ids = {create_guest_id("web") for _ in range(10)}
        assert len(ids) == 10  # all unique

    def test_guest_id_platform(self):
        assert create_guest_id("line").startswith("guest_line_")
        assert create_guest_id("discord").startswith("guest_discord_")


# ──────────────────────────────────────────────
# Memory Store — Auth Methods
# ──────────────────────────────────────────────
class TestMemoryStoreAuth:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.mark.asyncio
    async def test_create_and_find_user(self, store):
        user_data = {
            "user_id": "user_test1",
            "username": "findme",
            "auth_provider": "local",
        }
        await store.create_user(user_data)
        found = await store.find_user_by_username("findme")
        assert found is not None
        assert found["user_id"] == "user_test1"

    @pytest.mark.asyncio
    async def test_find_nonexistent_username(self, store):
        found = await store.find_user_by_username("ghost")
        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_google_id(self, store):
        user_data = {
            "user_id": "user_g1",
            "username": "google@test.com",
            "google_id": "google_123",
            "auth_provider": "google",
        }
        await store.create_user(user_data)
        found = await store.find_user_by_google_id("google_123")
        assert found is not None
        assert found["user_id"] == "user_g1"

    @pytest.mark.asyncio
    async def test_find_nonexistent_google_id(self, store):
        found = await store.find_user_by_google_id("nope_123")
        assert found is None

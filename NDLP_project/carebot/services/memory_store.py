"""
Memory Store — EVC state persistence

Primary: Azure Cosmos DB
Fallback: In-memory dictionary (for dev/testing)
"""
import os
import json
from typing import Optional
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.evc_models import EVCState
from evc.engine import create_initial_state


class InMemoryStore:
    """In-memory fallback when Cosmos DB is not configured"""

    def __init__(self):
        self._users: dict[str, dict] = {}
        self._conversations: dict[str, list[dict]] = {}
        print("[MemoryStore] Using in-memory store (dev mode)")

    async def get_evc_state(self, user_id: str) -> EVCState:
        """Get EVC state for a user, or create initial state"""
        if user_id in self._users and "evc_state" in self._users[user_id]:
            return EVCState(**self._users[user_id]["evc_state"])
        return create_initial_state()

    async def save_evc_state(self, user_id: str, state: EVCState) -> None:
        """Save EVC state for a user"""
        if user_id not in self._users:
            self._users[user_id] = {"user_id": user_id, "created_at": datetime.now().isoformat()}
        self._users[user_id]["evc_state"] = state.model_dump(mode="json")
        self._users[user_id]["updated_at"] = datetime.now().isoformat()

    async def add_message(self, user_id: str, message: dict) -> None:
        """Add a message to conversation history"""
        if user_id not in self._conversations:
            self._conversations[user_id] = []
        self._conversations[user_id].append(message)
        # Keep last 50 messages
        if len(self._conversations[user_id]) > 50:
            self._conversations[user_id] = self._conversations[user_id][-50:]

    async def get_conversation_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict]:
        """Get recent conversation history"""
        messages = self._conversations.get(user_id, [])
        return messages[-limit:]

    async def get_user(self, user_id: str) -> Optional[dict]:
        """Get user data"""
        return self._users.get(user_id)

    async def save_user(self, user_id: str, data: dict) -> None:
        """Save user data"""
        self._users[user_id] = data

    async def create_user(self, user_data: dict) -> dict:
        """Create a new user account"""
        user_id = user_data["user_id"]
        self._users[user_id] = user_data
        return user_data

    async def find_user_by_username(self, username: str) -> Optional[dict]:
        """Find user by username"""
        for data in self._users.values():
            if data.get("username") == username:
                return data
        return None

    async def find_user_by_google_id(self, google_id: str) -> Optional[dict]:
        """Find user by Google ID"""
        for data in self._users.values():
            if data.get("google_id") == google_id:
                return data
        return None

    async def get_all_users(self) -> list[dict]:
        """Get all users (for dashboard)"""
        return list(self._users.values())

    async def link_platforms(
        self, user_id: str, platform: str, platform_id: str
    ) -> None:
        """Link a platform ID to a user"""
        if user_id not in self._users:
            self._users[user_id] = {"user_id": user_id}
        if "platforms" not in self._users[user_id]:
            self._users[user_id]["platforms"] = {}
        self._users[user_id]["platforms"][platform] = platform_id

    async def find_user_by_platform(
        self, platform: str, platform_id: str
    ) -> Optional[str]:
        """Find user_id by platform and platform_id"""
        for uid, data in self._users.items():
            platforms = data.get("platforms", {})
            if platforms.get(platform) == platform_id:
                return uid
        return None


class CosmosStore:
    """Azure Cosmos DB store (for production)"""

    def __init__(self):
        from azure.cosmos.aio import CosmosClient

        endpoint = os.getenv("COSMOS_ENDPOINT", "")
        key = os.getenv("COSMOS_KEY", "")
        db_name = os.getenv("COSMOS_DATABASE", "carebot")
        container_name = os.getenv("COSMOS_CONTAINER", "users")

        self.client = CosmosClient(endpoint, credential=key)
        self.db = self.client.get_database_client(db_name)
        self.container = self.db.get_container_client(container_name)
        print(f"[MemoryStore] Using Cosmos DB: {db_name}/{container_name}")

    async def get_evc_state(self, user_id: str) -> EVCState:
        try:
            item = await self.container.read_item(item=user_id, partition_key=user_id)
            if "evc_state" in item:
                return EVCState(**item["evc_state"])
        except Exception:
            pass
        return create_initial_state()

    async def save_evc_state(self, user_id: str, state: EVCState) -> None:
        try:
            try:
                item = await self.container.read_item(item=user_id, partition_key=user_id)
            except Exception:
                item = {"id": user_id, "user_id": user_id}

            item["evc_state"] = state.model_dump(mode="json")
            item["updated_at"] = datetime.now().isoformat()
            await self.container.upsert_item(item)
        except Exception as e:
            print(f"[CosmosStore] Save failed: {e}")

    async def add_message(self, user_id: str, message: dict) -> None:
        try:
            msg_id = f"{user_id}_msg_{datetime.now().timestamp()}"
            item = {
                "id": msg_id,
                "user_id": user_id,
                "type": "message",
                **message,
            }
            await self.container.upsert_item(item)
        except Exception as e:
            print(f"[CosmosStore] Add message failed: {e}")

    async def get_conversation_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict]:
        try:
            query = (
                f"SELECT TOP {limit} * FROM c "
                f"WHERE c.user_id = '{user_id}' AND c.type = 'message' "
                f"ORDER BY c.timestamp DESC"
            )
            items = []
            async for item in self.container.query_items(
                query=query, partition_key=user_id
            ):
                items.append(item)
            return list(reversed(items))
        except Exception:
            return []

    async def create_user(self, user_data: dict) -> dict:
        """Create a new user account in Cosmos DB"""
        try:
            await self.container.upsert_item(user_data)
            return user_data
        except Exception as e:
            print(f"[CosmosStore] Create user failed: {e}")
            raise

    async def find_user_by_username(self, username: str) -> Optional[dict]:
        """Find user by username in Cosmos DB"""
        try:
            query = f"SELECT * FROM c WHERE c.username = '{username}' AND c.auth_provider != null"
            async for item in self.container.query_items(
                query=query, enable_cross_partition_query=True
            ):
                return item
        except Exception:
            pass
        return None

    async def find_user_by_google_id(self, google_id: str) -> Optional[dict]:
        """Find user by Google ID in Cosmos DB"""
        try:
            query = f"SELECT * FROM c WHERE c.google_id = '{google_id}'"
            async for item in self.container.query_items(
                query=query, enable_cross_partition_query=True
            ):
                return item
        except Exception:
            pass
        return None

    async def get_all_users(self) -> list[dict]:
        try:
            query = "SELECT * FROM c WHERE c.type != 'message'"
            items = []
            async for item in self.container.query_items(
                query=query, enable_cross_partition_query=True
            ):
                items.append(item)
            return items
        except Exception:
            return []


def create_memory_store():
    """
    Factory function — auto-detect Cosmos DB or use in-memory fallback
    """
    cosmos_endpoint = os.getenv("COSMOS_ENDPOINT", "placeholder")
    cosmos_key = os.getenv("COSMOS_KEY", "placeholder")

    if (
        cosmos_endpoint != "placeholder"
        and cosmos_key != "placeholder"
        and cosmos_endpoint
        and cosmos_key
    ):
        try:
            return CosmosStore()
        except Exception as e:
            print(f"[MemoryStore] Cosmos DB init failed: {e}, using in-memory")

    return InMemoryStore()

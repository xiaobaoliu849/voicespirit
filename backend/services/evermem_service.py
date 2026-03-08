"""
EverMemOS Service
Service for interacting with EverMemOS long-term memory system.
Supports both Cloud (https://api.evermind.ai) and self-hosted instances.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EverMemService:
    def __init__(self, api_url: str, api_key: str | None = None):
        self.api_url = (api_url or "https://api.evermind.ai").rstrip("/")
        self.api_key = api_key

    async def add_memory(
        self,
        content: str,
        user_id: str = "guest",
        sender: str | None = None,
        sender_name: str = "User",
        flush: bool = False,
    ) -> dict[str, Any] | None:
        """Add a memory to EverMemOS (v0 API)."""
        if not self.api_key:
            logger.warning("EverMemService: Missing API key. Cannot add memory.")
            return None

        message_id = str(uuid.uuid4())
        create_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        actual_sender = sender or user_id

        url = f"{self.api_url}/api/v0/memories"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "message_id": message_id,
            "create_time": create_time,
            "sender": actual_sender,
            "sender_name": sender_name,
            "content": content,
            "flush": flush,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Failed to add memory to EverMemOS: {e}")
            return None

    async def search_memories(
        self, query: str, user_id: str = "guest", min_score: float = 0.3
    ) -> list[dict[str, Any]]:
        """Search for relevant memories in EverMemOS (v0 API)."""
        if not self.api_key:
            logger.warning("EverMemService: Missing API key. Cannot search memories.")
            return []

        search_url = f"{self.api_url}/api/v0/memories/search"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {
            "user_id": user_id,
            "query": query,
            "retrieve_method": "hybrid",
            "top_k": 5,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(search_url, headers=headers, params=params)
                if resp.status_code != 200:
                    logger.error(f"EverMem search returned {resp.status_code}: {resp.text[:200]}")
                    return []

                data = resp.json()

            result = data.get("result", {})
            if not result:
                return []

            memories_list = result.get("memories", [])
            profiles_list = result.get("profiles", [])

            extracted_memories = []

            for profile in profiles_list:
                desc = profile.get("description")
                if desc:
                    extracted_memories.append(
                        {
                            "content": f"[用户画像] {desc}",
                            "type": "profile",
                            "score": profile.get("score", 1.0),
                        }
                    )

            for mem in memories_list:
                score = mem.get("score", 0.0)
                if score < min_score:
                    continue
                mem_type = mem.get("memory_type", "episodic_memory")
                content = mem.get("episode") or mem.get("summary") or mem.get("content")
                if content:
                    type_label = {
                        "episodic_memory": "历史对话",
                        "foresight": "提醒/行动",
                        "profile": "用户画像",
                    }.get(mem_type, "记忆")
                    extracted_memories.append(
                        {"content": f"[{type_label}] {content}", "type": mem_type, "score": score}
                    )

            return extracted_memories
        except Exception as e:
            logger.error(f"Failed to search memories in EverMemOS: {e}")
            return []

    async def get_memories(self, user_id: str = "guest") -> list[dict[str, Any]]:
        """Get all core memories for a user (v0 API)."""
        if not self.api_key:
            logger.warning("EverMemService: Missing API key. Cannot get memories.")
            return []

        search_url = f"{self.api_url}/api/v0/memories"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {
            "user_id": user_id,
            "memory_type": "episodic_memory",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(search_url, headers=headers, params=params)
                if resp.status_code != 200:
                    return []
                data = resp.json()

            result = data.get("result", {})
            if not result:
                return []

            memories_list = result.get("memories", [])
            extracted_memories = []
            for mem in memories_list:
                content = mem.get("episode") or mem.get("summary") or mem.get("content")
                if content:
                    extracted_memories.append({"content": content})
            return extracted_memories
        except Exception as e:
            logger.error(f"Failed to get memories from EverMemOS: {e}")
            return []

    _SKIP_PATTERNS = {
        "你好",
        "hello",
        "hi",
        "hey",
        "嗨",
        "哈喽",
        "早上好",
        "晚上好",
        "下午好",
        "好的",
        "ok",
        "okay",
        "嗯",
        "嗯嗯",
        "好",
        "行",
        "可以",
        "明白",
        "了解",
        "谢谢",
        "thanks",
        "thank you",
        "thx",
        "感谢",
        "多谢",
        "哈哈",
        "哈哈哈",
        "lol",
        "😂",
        "👍",
        "666",
        "厉害",
        "不错",
        "太棒了",
        "棒",
        "nice",
        "great",
        "cool",
        "wow",
        "再见",
        "拜拜",
        "bye",
        "晚安",
        "good night",
    }

    def should_skip_memory(self, user_msg: str) -> bool:
        """Lightweight local check to skip memory retrieval for trivial messages."""
        msg = user_msg.strip().lower().rstrip("!！~.。？?")
        if len(msg) <= 2:
            return True
        if msg in self._SKIP_PATTERNS:
            return True
        return False

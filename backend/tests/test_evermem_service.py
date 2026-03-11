from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from services.evermem_service import EverMemService


class EverMemServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_memory_aligns_sender_with_user_scope(self) -> None:
        service = EverMemService(api_url="https://memory.example.com", api_key="test-key")

        response = Mock()
        response.raise_for_status.return_value = None
        post = AsyncMock(return_value=response)

        with patch("services.evermem_service.httpx.AsyncClient") as client_cls:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            client.post = post
            client_cls.return_value = client

            result = await service.add_memory(
                content="remember this",
                user_id="scope-main",
                sender="scope-main_chat",
                sender_name="VoiceSpirit",
            )

        self.assertEqual(result, {"status": "success"})
        _, kwargs = post.call_args
        self.assertEqual(kwargs["json"]["user_id"], "scope-main")
        self.assertEqual(kwargs["json"]["sender"], "scope-main")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")

    async def test_search_memories_includes_pending_messages(self) -> None:
        service = EverMemService(api_url="https://memory.example.com", api_key="test-key")

        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "result": {
                "profiles": [],
                "memories": [],
                "pending_messages": [
                    {"content": "本周重点是比赛提交"},
                ],
            }
        }
        get = AsyncMock(return_value=response)

        with patch("services.evermem_service.httpx.AsyncClient") as client_cls:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            client.get = get
            client_cls.return_value = client

            result = await service.search_memories(
                query="本周重点工作是什么",
                user_id="scope-main",
                memory_types=["episodic_memory", "profile"],
            )

        self.assertEqual(len(result), 1)
        self.assertIn("待处理消息", result[0]["content"])
        _, kwargs = get.call_args
        self.assertEqual(kwargs["params"]["user_id"], "scope-main")
        self.assertEqual(kwargs["params"]["memory_types"], ["episodic_memory", "profile"])


if __name__ == "__main__":
    unittest.main()

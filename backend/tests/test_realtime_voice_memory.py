from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from services.evermem_service import EverMemService
from services.realtime_voice_service import RealtimeMemorySession, RealtimeVoiceService


class RealtimeMemorySessionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        RealtimeMemorySession._PENDING_CACHE_PATH = Path(self.temp_dir.name) / "pending.json"
        RealtimeMemorySession._PENDING_MEMORY_CACHE.clear()

    def tearDown(self) -> None:
        RealtimeMemorySession._PENDING_MEMORY_CACHE.clear()
        self.temp_dir.cleanup()

    async def test_flush_turn_persists_only_structured_voice_memory(self) -> None:
        session = RealtimeMemorySession()
        session.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        session.note_user_transcript("以后比赛提交阶段默认都用中文女声来播报。")
        session.note_assistant_text("好的，我们先检查记忆接入状态。")

        with patch.object(
            EverMemService,
            "add_memory",
            new=AsyncMock(return_value={"status": "success"}),
        ) as add_memory:
            result = await session.flush_turn()

        self.assertEqual(add_memory.await_count, 1)
        self.assertEqual(result["saved_count"], 1)
        self.assertEqual(result["local_pending_count"], 1)
        first_call = add_memory.await_args_list[0]
        self.assertEqual(first_call.kwargs["user_id"], "voice-demo")
        self.assertEqual(first_call.kwargs["sender"], "voice-demo")
        self.assertIn("语音偏好", first_call.kwargs["content"])

    async def test_trivial_question_does_not_persist_memory(self) -> None:
        session = RealtimeMemorySession()
        session.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        session.note_user_transcript("现在几点了？")

        with patch.object(
            EverMemService,
            "add_memory",
            new=AsyncMock(return_value={"status": "success"}),
        ) as add_memory:
            result = await session.flush_turn()

        add_memory.assert_not_awaited()
        self.assertEqual(result["reason"], "no_candidate_memory")

    async def test_config_false_disables_memory_flush(self) -> None:
        session = RealtimeMemorySession()
        session.configure({"enabled": False})
        session.note_user_transcript("以后都用女声。")

        with patch.object(
            EverMemService,
            "add_memory",
            new=AsyncMock(return_value={"status": "success"}),
        ) as add_memory:
            result = await session.flush_turn()

        add_memory.assert_not_awaited()
        self.assertEqual(result["reason"], "disabled_or_empty")

    async def test_retrieve_memory_context_for_recall_query(self) -> None:
        session = RealtimeMemorySession()
        session.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        session.note_user_transcript("我之前默认用什么声音来着？")

        with patch.object(
            EverMemService,
            "search_memories",
            new=AsyncMock(
                return_value=[
                    {"content": "[语音偏好] 默认使用中文女声播报", "score": 0.91},
                    {"content": "[任务] 当前重点是比赛提交", "score": 0.72},
                ]
            ),
        ) as search_memories:
            result = await session.retrieve_memory_context()

        self.assertIn("默认使用中文女声播报", result["context"])
        self.assertEqual(result["memories_retrieved"], 2)
        self.assertEqual(result["cloud_count"], 2)
        self.assertEqual(result["local_pending_count"], 0)
        self.assertEqual(search_memories.await_count, 1)

    async def test_retrieve_memory_context_for_task_question(self) -> None:
        session = RealtimeMemorySession()
        session.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        session.note_user_transcript("你帮我检索一下本周的重点工作是什么？")

        with patch.object(
            EverMemService,
            "search_memories",
            new=AsyncMock(
                return_value=[
                    {"content": "[任务] 当前重点是比赛提交", "score": 0.88},
                ]
            ),
        ) as search_memories:
            result = await session.retrieve_memory_context()

        self.assertIn("当前重点是比赛提交", result["context"])
        self.assertEqual(result["memories_retrieved"], 1)
        self.assertEqual(search_memories.await_count, 1)

    async def test_forced_recall_query_uses_longer_timeout_budget(self) -> None:
        session = RealtimeMemorySession()
        session.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        session.note_user_transcript("帮我回忆一下我们刚才说的重点工作是什么？")

        captured_timeout: float | None = None

        async def fake_wait_for(awaitable, timeout):
            nonlocal captured_timeout
            captured_timeout = timeout
            return await awaitable

        with patch("services.realtime_voice_service.asyncio.wait_for", new=fake_wait_for):
            with patch.object(
                EverMemService,
                "search_memories",
                new=AsyncMock(return_value=[]),
            ):
                await session.retrieve_memory_context()

        self.assertEqual(captured_timeout, 0.35)

    async def test_retrieve_memory_context_skips_trivial_turns(self) -> None:
        session = RealtimeMemorySession()
        session.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        session.note_user_transcript("你好")

        with patch.object(
            EverMemService,
            "search_memories",
            new=AsyncMock(return_value=[]),
        ) as search_memories:
            result = await session.retrieve_memory_context()

        self.assertEqual(result["context"], "")
        self.assertEqual(result["memories_retrieved"], 0)
        self.assertFalse(result["attempted"])
        search_memories.assert_not_awaited()

    def test_forced_recall_query_detection(self) -> None:
        session = RealtimeMemorySession()
        session.note_user_transcript("你还记得我们刚才说的重点工作是什么吗？")
        self.assertTrue(session.is_forced_recall_query())
        session.note_user_transcript("今天上海天气怎么样？")
        self.assertFalse(session.is_forced_recall_query())

    async def test_retrieve_memory_context_uses_local_pending_fallback(self) -> None:
        writer = RealtimeMemorySession()
        writer.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        writer.note_user_transcript("本周的重点是比赛提交，以后默认用中文回答。")

        with patch.object(
            EverMemService,
            "add_memory",
            new=AsyncMock(return_value={"status": "success"}),
        ):
            await writer.flush_turn()

        reader = RealtimeMemorySession()
        reader.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        reader.note_user_transcript("你还记得我们刚才说的本周重点工作是什么吗？")

        with patch.object(
            EverMemService,
            "search_memories",
            new=AsyncMock(return_value=[]),
        ):
            result = await reader.retrieve_memory_context()

        self.assertEqual(result["memories_retrieved"], 1)
        self.assertEqual(result["local_pending_count"], 1)
        self.assertEqual(result["cloud_count"], 0)
        self.assertIn("本地待同步记忆", result["context"])

    async def test_retrieve_memory_context_uses_persisted_pending_fallback_after_restart(self) -> None:
        writer = RealtimeMemorySession()
        writer.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        writer.note_user_transcript("本周的重点是比赛提交，以后默认用中文回答。")

        with patch.object(
            EverMemService,
            "add_memory",
            new=AsyncMock(return_value={"status": "success"}),
        ):
            await writer.flush_turn()

        RealtimeMemorySession._PENDING_MEMORY_CACHE.clear()

        reader = RealtimeMemorySession()
        reader.configure(
            {
                "enabled": True,
                "api_url": "https://memory.example.com",
                "api_key": "memory-key",
                "scope_id": "voice-demo",
            }
        )
        reader.note_user_transcript("你还记得我们刚才说的本周重点工作是什么吗？")

        with patch.object(
            EverMemService,
            "search_memories",
            new=AsyncMock(return_value=[]),
        ):
            result = await reader.retrieve_memory_context()

        self.assertEqual(result["memories_retrieved"], 1)
        self.assertEqual(result["local_pending_count"], 1)
        self.assertEqual(result["cloud_count"], 0)
        self.assertIn("本地待同步记忆", result["context"])

    async def test_google_memory_prefill_sends_client_content(self) -> None:
        service = RealtimeVoiceService()
        fake_session = AsyncMock()

        await service._apply_google_memory_prefill(
            fake_session,
            "1. [语音偏好] 默认使用中文女声播报",
        )

        fake_session.send_client_content.assert_awaited_once()
        kwargs = fake_session.send_client_content.await_args.kwargs
        self.assertFalse(kwargs["turn_complete"])
        self.assertIn("默认使用中文女声播报", kwargs["turns"][0]["parts"][0]["text"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.realtime_voice_service import RealtimeVoiceService, VoiceAgentSessionRecorder
from services.voice_agent_session_repository import VoiceAgentSessionRepository


class VoiceAgentSessionRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "voice_spirit_test.db"
        self.repository = VoiceAgentSessionRepository(db_path=self.db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_persists_session_turn_and_tool_event(self) -> None:
        session = self.repository.create_session(
            provider="DashScope",
            model="qwen-realtime",
            voice="Cherry",
            meta={"transport": "websocket"},
        )

        self.repository.upsert_turn(
            session["id"],
            "voice-tool-1",
            user_text="帮我搜索语音 Agent",
        )
        self.repository.add_tool_event(
            session["id"],
            "agent_result",
            {
                "tool_name": "search_web",
                "turn_id": "voice-tool-1",
                "query": "语音 Agent",
                "answer": "已整理结果",
                "sources": [{"title": "Source", "uri": "https://example.com"}],
            },
        )
        self.repository.upsert_turn(
            session["id"],
            "voice-tool-1",
            assistant_text="这是基于来源的回答。",
            memory_payload={"saved_count": 1},
            completed=True,
        )
        self.repository.finish_session(session["id"])

        stored = self.repository.get_session(session["id"])
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["status"], "closed")

        turns = self.repository.list_turns(session["id"])
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["turn_id"], "voice-tool-1")
        self.assertEqual(turns[0]["user_text"], "帮我搜索语音 Agent")
        self.assertEqual(turns[0]["assistant_text"], "这是基于来源的回答。")
        self.assertTrue(turns[0]["completed"])
        self.assertEqual(turns[0]["memory_payload"]["saved_count"], 1)

        events = self.repository.list_tool_events(session["id"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "agent_result")
        self.assertEqual(events[0]["tool_name"], "search_web")
        self.assertEqual(events[0]["payload"]["sources"][0]["title"], "Source")

        timeline = self.repository.build_timeline(session["id"])
        self.assertEqual(
            [event["event_type"] for event in timeline],
            [
                "session_open",
                "user_transcript",
                "agent_result",
                "assistant_response",
                "memory_commit",
                "turn_completed",
                "session_closed",
            ],
        )
        self.assertEqual(timeline[1]["text"], "帮我搜索语音 Agent")
        self.assertEqual(timeline[2]["source"], "tool_event")
        self.assertEqual(timeline[2]["payload"]["answer"], "已整理结果")
        self.assertEqual(timeline[3]["text"], "这是基于来源的回答。")
        self.assertEqual(timeline[4]["payload"]["saved_count"], 1)

    async def test_recorder_links_tool_events_to_current_transcript_turn(self) -> None:
        session = self.repository.create_session(
            provider="Google",
            model="gemini-live",
            voice="Puck",
        )
        recorder = VoiceAgentSessionRecorder(self.repository, session["id"])

        await recorder.note_user_transcript("帮我搜索 AI voice agent")
        await recorder.record_tool_event(
            "tool_call_started",
            {
                "tool_name": "search_web",
                "turn_id": "voice-tool-1",
                "query": "AI voice agent",
            },
        )
        await recorder.record_tool_event(
            "agent_result",
            {
                "tool_name": "search_web",
                "turn_id": "voice-tool-1",
                "query": "AI voice agent",
                "answer": "我查到这些信息。",
                "sources": [],
            },
        )
        await recorder.note_assistant_text("我查到这些信息。")
        await recorder.complete_turn({"attempted_count": 1, "saved_count": 0})

        turns = self.repository.list_turns(session["id"])
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["turn_id"], "voice-tool-1")
        self.assertEqual(turns[0]["user_text"], "帮我搜索 AI voice agent")
        self.assertEqual(turns[0]["assistant_text"], "我查到这些信息。")
        self.assertTrue(turns[0]["completed"])
        self.assertEqual(turns[0]["memory_payload"]["attempted_count"], 1)

        events = self.repository.list_tool_events(session["id"])
        self.assertEqual([event["event_type"] for event in events], ["tool_call_started", "agent_result"])
        self.assertEqual(events[1]["payload"]["answer"], "我查到这些信息。")

    async def test_realtime_service_creates_session_recorder(self) -> None:
        service = RealtimeVoiceService(voice_session_repository=self.repository)

        recorder = await service._create_voice_session_recorder(
            provider="DashScope",
            model="qwen-realtime",
            voice="Cherry",
        )

        self.assertIsNotNone(recorder)
        assert recorder is not None
        stored = self.repository.get_session(recorder.session_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["provider"], "DashScope")
        self.assertEqual(stored["model"], "qwen-realtime")
        self.assertEqual(stored["voice"], "Cherry")
        self.assertEqual(stored["meta"]["transport"], "websocket")


if __name__ == "__main__":
    unittest.main()

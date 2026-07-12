from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from services.agent_run_repository import AgentRunRepository
from services.agent_run_service import AgentRunService
from services.audio_agent_service import AudioAgentService
from services.realtime_voice_service import VoiceAgentSessionRecorder
from services.voice_agent_session_repository import VoiceAgentSessionRepository


class AgentRunRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "agent_runs.db"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_projects_and_refreshes_existing_audio_run(self) -> None:
        audio_service = AudioAgentService(db_path=self.db_path)
        source = audio_service.create_run(topic="统一 Run 测试", auto_execute=False)
        repository = AgentRunRepository(db_path=self.db_path)
        canonical_id = repository.canonical_audio_run_id(source["id"])

        projected = repository.get_run(canonical_id)
        self.assertIsNotNone(projected)
        assert projected is not None
        self.assertEqual(projected["source_run_id"], str(source["id"]))
        self.assertEqual(projected["title"], "统一 Run 测试")
        self.assertEqual(projected["status"], "queued")

        first_link = repository.link_voice_turn(
            agent_run_id=canonical_id,
            voice_session_id="voice-session-1",
            voice_turn_id="voice-turn-1",
            meta={"attempt": 1},
        )
        repeated_link = repository.link_voice_turn(
            agent_run_id=canonical_id,
            voice_session_id="voice-session-1",
            voice_turn_id="voice-turn-1",
            meta={"attempt": 2},
        )
        self.assertEqual(repeated_link["id"], first_link["id"])
        self.assertEqual(repeated_link["meta"], {"attempt": 2})

        audio_service.repository.update_run(int(source["id"]), status="cancelled")
        linked = repository.list_links_for_session("voice-session-1")
        self.assertEqual(linked[0]["run"]["status"], "cancelled")
        service = AgentRunService(
            repository=repository,
            audio_agent_service=audio_service,
        )
        refreshed = service.get_run(canonical_id)
        self.assertEqual(refreshed["status"], "cancelled")

    async def test_recorder_creates_durable_voice_turn_link(self) -> None:
        voice_repository = VoiceAgentSessionRepository(db_path=self.db_path)
        session = voice_repository.create_session(
            provider="Google",
            model="gemini-live",
            voice="Puck",
        )
        recorder = VoiceAgentSessionRecorder(voice_repository, session["id"])
        await recorder.note_user_transcript("做一期 AI 播客")
        await recorder.record_tool_event(
            "agent_result",
            {
                "tool_name": "create_audio_agent_run",
                "turn_id": "voice-tool-1",
                "query": "AI 播客",
                "artifact": {
                    "type": "audio_agent_run",
                    "run_id": 42,
                    "status": "queued",
                    "topic": "AI 播客",
                    "current_step": "retrieve",
                    "provider": "DashScope",
                },
            },
        )

        links = voice_repository.list_agent_run_links(session["id"])
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["agent_run_id"], "audio_agent:42")
        self.assertEqual(links[0]["voice_turn_id"], "voice-tool-1")
        self.assertEqual(links[0]["run"]["title"], "AI 播客")
        tool_event = voice_repository.list_tool_events(session["id"])[0]
        self.assertEqual(tool_event["payload"]["artifact"]["agent_run_id"], "audio_agent:42")
        event_types = [event["event_type"] for event in voice_repository.list_session_events(session["id"])]
        self.assertIn("agent_run_linked", event_types)

    def test_migration_backfills_audio_runs_and_voice_artifact_links(self) -> None:
        audio_service = AudioAgentService(db_path=self.db_path)
        source = audio_service.create_run(topic="旧任务", auto_execute=False)
        voice_repository = VoiceAgentSessionRepository(db_path=self.db_path)
        session = voice_repository.create_session(
            provider="DashScope",
            model="qwen-realtime",
            voice="Cherry",
        )
        voice_repository.upsert_turn(session["id"], "voice-tool-legacy", user_text="创建旧任务")
        voice_repository.add_tool_event(
            session["id"],
            "agent_result",
            {
                "tool_name": "create_audio_agent_run",
                "turn_id": "voice-tool-legacy",
                "artifact": {
                    "type": "audio_agent_run",
                    "run_id": int(source["id"]),
                    "status": "queued",
                    "topic": "旧任务",
                },
            },
        )
        audio_service.repository.update_run(int(source["id"]), status="cancelled")
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DROP TABLE agent_run_links")
            conn.execute("DROP TABLE agent_runs")
            conn.commit()
        finally:
            conn.close()

        migrated = AgentRunRepository(db_path=self.db_path)
        links = migrated.list_links_for_session(session["id"])
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["voice_turn_id"], "voice-tool-legacy")
        self.assertEqual(links[0]["run"]["source_run_id"], str(source["id"]))
        self.assertEqual(links[0]["run"]["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()

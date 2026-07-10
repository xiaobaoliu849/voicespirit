import unittest
import tempfile
from pathlib import Path
from services.voice_agent_session_repository import VoiceAgentSessionRepository

class TestTimelineReplay(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "voice_spirit_test.db"
        self.repo = VoiceAgentSessionRepository(db_path=self.db_path)
        session = self.repo.create_session(
            provider="DashScope",
            model="qwen-realtime",
            voice="Cherry",
            meta={"transport": "websocket"}
        )
        self.session_id = session["id"]

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_search_flow_timeline(self):
        # User speaks
        self.repo.upsert_turn(
            session_id=self.session_id,
            turn_id="turn-1",
            user_text="帮我搜索天气",
            completed=False
        )

        # Tool started
        self.repo.add_tool_event(
            session_id=self.session_id,
            event_type="tool_call_started",
            payload={"turn_id": "turn-1", "tool_name": "search_web", "query": "北京天气", "stage": "started"}
        )

        # Tool completed
        self.repo.add_tool_event(
            session_id=self.session_id,
            event_type="tool_call_completed",
            payload={"turn_id": "turn-1", "tool_name": "search_web", "query": "北京天气", "answer": "今天晴朗", "elapsed_ms": 1500, "stage": "completed"}
        )

        # Agent response
        self.repo.upsert_turn(
            session_id=self.session_id,
            turn_id="turn-1",
            user_text="帮我搜索天气",
            assistant_text="今天北京晴朗。",
            completed=True
        )

        timeline = self.repo.build_timeline(self.session_id)

        # event_types expected: session_open, user_transcript, tool_call_started, tool_call_completed, assistant_response
        event_types = [e["event_type"] for e in timeline]
        self.assertEqual(event_types, [
            "session_open",
            "user_transcript",
            "tool_call_started",
            "tool_call_completed",
            "assistant_response",
            "turn_completed"
        ])

        # Check metrics
        completed_tool_event = next(e for e in timeline if e["event_type"] == "tool_call_completed")
        self.assertEqual(completed_tool_event["elapsed_ms"], 1500)
        self.assertEqual(completed_tool_event["stage"], "completed")

        for e in timeline:
            self.assertEqual(e["provider"], "DashScope")
            self.assertEqual(e["transport"], "websocket")

    def test_interruption_flow_timeline(self):
        # User speaks
        self.repo.upsert_turn(
            session_id=self.session_id,
            turn_id="turn-2",
            user_text="帮我查",
            completed=False
        )

        # Tool started
        self.repo.add_tool_event(
            session_id=self.session_id,
            event_type="tool_call_started",
            payload={"turn_id": "turn-2", "tool_name": "search_web", "query": "查", "stage": "started"}
        )

        # Tool cancelled
        self.repo.add_tool_event(
            session_id=self.session_id,
            event_type="tool_call_cancelled",
            payload={"turn_id": "turn-2", "tool_name": "search_web", "query": "查", "stage": "cancelled", "elapsed_ms": 200}
        )

        # Turn completed (interrupted)
        self.repo.upsert_turn(
            session_id=self.session_id,
            turn_id="turn-2",
            user_text="帮我查",
            assistant_text="",
            completed=True
        )

        timeline = self.repo.build_timeline(self.session_id)

        event_types = [e["event_type"] for e in timeline]
        self.assertEqual(event_types, [
            "session_open",
            "user_transcript",
            "tool_call_started",
            "tool_call_cancelled",
            "turn_completed"
        ])

        cancelled_tool = next(e for e in timeline if e["event_type"] == "tool_call_cancelled")
        self.assertEqual(cancelled_tool["elapsed_ms"], 200)

    def test_memory_write_flow_timeline(self):
        # Turn with memory payload
        self.repo.upsert_turn(
            session_id=self.session_id,
            turn_id="turn-3",
            user_text="我喜欢吃苹果",
            assistant_text="记住了",
            completed=True,
            memory_payload={"saved": True, "fact": "用户喜欢吃苹果"}
        )

        timeline = self.repo.build_timeline(self.session_id)

        event_types = [e["event_type"] for e in timeline]
        self.assertEqual(event_types, [
            "session_open",
            "user_transcript",
            "assistant_response",
            "memory_commit",
            "turn_completed"
        ])

        memory_event = next(e for e in timeline if e["event_type"] == "memory_commit")
        self.assertEqual(memory_event["payload"]["fact"], "用户喜欢吃苹果")

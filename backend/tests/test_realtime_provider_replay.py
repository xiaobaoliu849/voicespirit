import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.interruption_classifier import InterruptionDecisionCoordinator
from services.realtime_voice_service import (
    DashScopeRealtimeCallback,
    RealtimeVoiceService,
    VoiceAgentSessionRecorder,
)
from services.voice_agent_session_repository import VoiceAgentSessionRepository


class ReplayComplete(Exception):
    pass


class FakeClock:
    def __init__(self) -> None:
        self.values = iter((10.0, 10.037))

    def __call__(self) -> float:
        return next(self.values)


class CollectingWebSocket:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.events.append(dict(payload))


class FakeMemorySession:
    def __init__(self) -> None:
        self.user_texts: list[str] = []
        self.assistant_texts: list[str] = []
        self._config = SimpleNamespace(memory_scope="", group_id="")

    def note_user_transcript(self, text: str) -> None:
        self.user_texts.append(text)

    def note_assistant_text(self, text: str) -> None:
        self.assistant_texts.append(text)

    async def retrieve_memory_context(self) -> dict:
        return {
            "context": "",
            "memories_retrieved": 0,
            "local_pending_count": 0,
            "cloud_count": 0,
            "attempted": False,
        }

    async def flush_turn(self) -> dict:
        return {
            "attempted_count": 0,
            "saved_count": 0,
            "failed_count": 0,
            "local_pending_count": 0,
            "reason": "disabled",
        }

    def is_forced_recall_query(self, _text: str) -> bool:
        return False


class RecordingToolSession:
    def __init__(self, *, active: bool) -> None:
        self.active = active
        self.cancel_count = 0
        self.cancel_reasons: list[str] = []
        self.handled_texts: list[str] = []

    @property
    def has_active_task(self) -> bool:
        return self.active

    @property
    def current_turn_id(self) -> str:
        return "existing-tool" if self.active else ""

    async def cancel(self, *, send_event, reason: str = "cancelled") -> None:
        if not self.active:
            return
        self.cancel_count += 1
        self.cancel_reasons.append(reason)
        self.active = False
        await send_event(
            "tool_call_cancelled",
            {
                "tool_name": "search_web",
                "turn_id": "existing-tool",
                "query": "original query",
                "reason": reason,
                "elapsed_ms": 37,
            },
        )

    async def handle_user_transcript(self, text: str, **_kwargs) -> str:
        self.handled_texts.append(text)
        return ""


class FakeGoogleSession:
    def __init__(self, batches: list[list[SimpleNamespace]]) -> None:
        self.batches = list(batches)
        self.sent: list[dict] = []

    def receive(self):
        if not self.batches:
            raise ReplayComplete()
        batch = self.batches.pop(0)

        async def iterator():
            for item in batch:
                yield item

        return iterator()

    async def send(self, **payload) -> None:
        self.sent.append(dict(payload))


class FakeOpenAIWebSocket:
    def __init__(self, events: list[dict]) -> None:
        self.events = list(events)
        self.sent: list[dict] = []

    def __aiter__(self):
        async def iterator():
            for event in self.events:
                yield json.dumps(event)

        return iterator()

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))


def google_response(**server_content_fields) -> SimpleNamespace:
    return SimpleNamespace(
        data=None,
        text=None,
        server_content=SimpleNamespace(**server_content_fields),
    )


class RealtimeProviderReplayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = VoiceAgentSessionRepository(Path(self.temp_dir.name) / "voice.db")
        self.service = RealtimeVoiceService(voice_session_repository=self.repository)

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def _recorder(self, provider: str) -> VoiceAgentSessionRecorder:
        session = self.repository.create_session(
            provider=provider,
            model=f"{provider.lower()}-replay",
            voice="test-voice",
            meta={"transport": "websocket"},
        )
        recorder = VoiceAgentSessionRecorder(self.repository, session["id"])
        await recorder.start(
            {
                "provider": provider,
                "model": f"{provider.lower()}-replay",
                "voice": "test-voice",
                "status": "open",
                "meta": {"transport": "websocket"},
            }
        )
        await recorder.note_user_transcript("请解释实时语音")
        await recorder.note_assistant_text("这是还没有说完的回答")
        return recorder

    async def _replay(self, provider: str, transcript: str, *, true_barge_in: bool) -> dict:
        websocket = CollectingWebSocket()
        memory = FakeMemorySession()
        tools = RecordingToolSession(active=true_barge_in)
        recorder = await self._recorder(provider)

        coordinator_factory = lambda: InterruptionDecisionCoordinator(clock=FakeClock())
        with patch(
            "services.realtime_voice_service.InterruptionDecisionCoordinator",
            side_effect=coordinator_factory,
        ):
            if provider == "DashScope":
                queue: asyncio.Queue[dict] = asyncio.Queue()
                callback = DashScopeRealtimeCallback(loop=asyncio.get_running_loop(), queue=queue)
                callback.on_event({"type": "response.created", "response": {"id": "response-1"}})
                callback.on_event(
                    {
                        "type": "input_audio_buffer.speech_started",
                        "event_id": "vad-1",
                        "item_id": "item-1",
                        "audio_start_ms": 100,
                    }
                )
                callback.on_event(
                    {
                        "type": "conversation.item.input_audio_transcription.completed",
                        "item_id": "item-1",
                        "transcript": transcript,
                    }
                )
                if not true_barge_in:
                    callback.on_event(
                        {"type": "response.done", "response": {"id": "response-1", "status": "completed"}}
                    )
                callback.on_close(1000, "replay complete")
                conversation = MagicMock()
                await self.service._dashscope_to_client_loop(
                    websocket,
                    queue,
                    memory,
                    conversation,
                    "test-voice",
                    tools,
                    recorder,
                )
                provider_stop_count = conversation.cancel_response.call_count
            elif provider == "OpenAI":
                raw_events = [
                    {"type": "response.created", "response": {"id": "response-1"}},
                    {"type": "input_audio_buffer.speech_started", "item_id": "item-1"},
                    {
                        "type": "conversation.item.input_audio_transcription.completed",
                        "item_id": "item-1",
                        "transcript": transcript,
                    },
                ]
                if not true_barge_in:
                    raw_events.append(
                        {"type": "response.done", "response": {"id": "response-1", "status": "completed"}}
                    )
                upstream = FakeOpenAIWebSocket(raw_events)
                await self.service._openai_to_client_loop(
                    websocket,
                    upstream,
                    memory,
                    tools,
                    recorder,
                )
                provider_stop_count = sum(item.get("type") == "response.cancel" for item in upstream.sent)
            else:
                batches = [
                    [google_response(interrupted=True)],
                    [google_response(input_transcription=SimpleNamespace(text=transcript))],
                ]
                if not true_barge_in:
                    batches.append([google_response(turn_complete=True)])
                session = FakeGoogleSession(batches)
                with self.assertRaises(ReplayComplete):
                    await self.service._google_to_client_loop(
                        websocket,
                        session,
                        memory,
                        tools,
                        recorder,
                    )
                # Google reports a provider-native interruption before transcription;
                # the public Live session has no explicit response.cancel method.
                provider_stop_count = 1 if true_barge_in else 0

        await recorder.finish()
        return {
            "events": websocket.events,
            "timeline": self.repository.build_timeline(recorder.session_id),
            "turns": self.repository.list_turns(recorder.session_id),
            "tool_cancel_count": tools.cancel_count,
            "provider_stop_count": provider_stop_count,
            "handled_texts": tools.handled_texts,
        }

    @staticmethod
    def _canonical_timeline(timeline: list[dict]) -> list[dict]:
        canonical = []
        for event in timeline:
            payload = event.get("payload", {})
            canonical.append(
                {
                    "event_type": event["event_type"],
                    "turn_id": event.get("turn_id", ""),
                    "text": event.get("text", ""),
                    "classification": payload.get("classification"),
                    "decision": payload.get("decision"),
                    "rule": payload.get("rule"),
                    "elapsed_ms": payload.get("elapsed_ms"),
                    "interrupted": payload.get("interrupted"),
                    "status": payload.get("status"),
                }
            )
        return canonical

    async def test_backchannel_keeps_answer_and_canonical_timeline_consistent(self) -> None:
        results = {
            provider: await self._replay(provider, "嗯嗯", true_barge_in=False)
            for provider in ("Google", "DashScope", "OpenAI")
        }
        for provider, result in results.items():
            with self.subTest(provider=provider):
                event_types = [event["type"] for event in result["events"]]
                self.assertIn("interruption_pending", event_types)
                self.assertIn("interruption_decision", event_types)
                self.assertNotIn("interrupted", event_types)
                decision = next(event for event in result["events"] if event["type"] == "interruption_decision")
                self.assertEqual(decision["classification"], "BACKCHANNEL")
                self.assertEqual(decision["elapsed_ms"], 37)
                self.assertEqual(result["tool_cancel_count"], 0)
                self.assertEqual(result["provider_stop_count"], 0)
                self.assertEqual(result["handled_texts"], [])
                self.assertEqual(len(result["turns"]), 1)
                self.assertFalse(result["turns"][0]["interrupted"])
        canonical = [self._canonical_timeline(result["timeline"]) for result in results.values()]
        self.assertEqual(canonical[0], canonical[1])
        self.assertEqual(canonical[1], canonical[2])

    async def test_true_barge_in_stops_answer_cancels_tools_and_preserves_boundary(self) -> None:
        results = {
            provider: await self._replay(provider, "等一下", true_barge_in=True)
            for provider in ("Google", "DashScope", "OpenAI")
        }
        for provider, result in results.items():
            with self.subTest(provider=provider):
                event_types = [event["type"] for event in result["events"]]
                self.assertLess(event_types.index("interruption_pending"), event_types.index("interruption_decision"))
                self.assertLess(event_types.index("interruption_decision"), event_types.index("interrupted"))
                decision = next(event for event in result["events"] if event["type"] == "interruption_decision")
                self.assertEqual(decision["classification"], "TRUE_BARGE_IN")
                self.assertEqual(result["tool_cancel_count"], 1)
                self.assertEqual(result["provider_stop_count"], 1)
                self.assertEqual(result["handled_texts"], ["等一下"])
                self.assertEqual(len(result["turns"]), 2)
                self.assertTrue(result["turns"][0]["interrupted"])
                self.assertEqual(result["turns"][0]["assistant_text"], "这是还没有说完的回答")
                self.assertEqual(result["turns"][1]["user_text"], "等一下")
        canonical = [self._canonical_timeline(result["timeline"]) for result in results.values()]
        self.assertEqual(canonical[0], canonical[1])
        self.assertEqual(canonical[1], canonical[2])

    async def test_noise_does_not_create_a_turn_or_cancel_answer(self) -> None:
        results = {
            provider: await self._replay(provider, "。！？", true_barge_in=False)
            for provider in ("Google", "DashScope", "OpenAI")
        }
        for provider, result in results.items():
            with self.subTest(provider=provider):
                decision = next(event for event in result["events"] if event["type"] == "interruption_decision")
                self.assertEqual(decision["classification"], "NOISE_OR_SILENCE")
                self.assertNotIn("interrupted", [event["type"] for event in result["events"]])
                self.assertEqual(result["tool_cancel_count"], 0)
                self.assertEqual(result["provider_stop_count"], 0)
                self.assertEqual(result["handled_texts"], [])
                self.assertEqual(len(result["turns"]), 1)
        canonical = [self._canonical_timeline(result["timeline"]) for result in results.values()]
        self.assertEqual(canonical[0], canonical[1])
        self.assertEqual(canonical[1], canonical[2])


if __name__ == "__main__":
    unittest.main()

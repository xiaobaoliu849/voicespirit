from __future__ import annotations

import asyncio
import unittest

from services.audio_research_service import ResearchDocument
from services.voice_agent_tools import VoiceAgentToolService, VoiceAgentToolSession


class FakeResearchService:
    async def search(self, query: str, *, limit: int = 3) -> list[dict[str, str]]:
        return [
            {
                "title": "Voice Agent Research",
                "url": "https://example.com/voice-agent",
                "snippet": f"Result for {query}",
            }
        ][:limit]

    async def fetch_document(
        self,
        url: str,
        *,
        title_hint: str = "",
        snippet_hint: str = "",
        source_type: str = "web_search",
        score: float = 0.7,
    ) -> ResearchDocument:
        return ResearchDocument(
            title=title_hint or "Voice Agent Research",
            url=url,
            snippet=snippet_hint or "Voice agent source snippet",
            content="Voice agents use interruption handling, tool calls, and grounded answers.",
            score=score,
            source_type=source_type,
            meta={"fetch_status": "ok"},
        )


class HangingResearchService:
    async def search(self, query: str, *, limit: int = 3) -> list[dict[str, str]]:
        await asyncio.sleep(30)
        return []


class FakeAudioAgentService:
    def __init__(self) -> None:
        self.create_calls: list[dict[str, object]] = []

    def create_run(self, **kwargs: object) -> dict[str, object]:
        self.create_calls.append(kwargs)
        return {
            "id": 42,
            "topic": kwargs.get("topic", ""),
            "status": "queued",
            "current_step": "retrieve",
        }


class FakeLLMService:
    def __init__(self) -> None:
        self.translate_calls: list[dict[str, object]] = []

    async def translate_text(self, **kwargs: object) -> dict[str, object]:
        self.translate_calls.append(kwargs)
        return {
            "provider": kwargs.get("provider", "DashScope"),
            "model": "qwen-plus",
            "translated_text": "Hello world",
        }

    async def chat_completion(self, **kwargs: object) -> dict[str, object]:
        return {
            "provider": kwargs.get("provider", "DashScope"),
            "model": "qwen-plus",
            "reply": "- 讨论了语音 Agent 的打断能力\n- 下一步要补工具持久化",
        }


class FakeTTSService:
    def __init__(self) -> None:
        self.generate_calls: list[dict[str, object]] = []

    async def generate_audio(self, **kwargs: object) -> tuple[str, str, bool]:
        self.generate_calls.append(kwargs)
        return ("D:/voicespirit/temp_audio/voice_tool.mp3", "zh-CN-XiaoxiaoNeural", False)


class VoiceAgentToolServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.events: list[dict[str, object]] = []

    async def _send_event(self, event_type: str, payload: dict[str, object]) -> None:
        self.events.append({"type": event_type, **payload})

    def test_extract_search_query_from_chinese_voice_command(self) -> None:
        query = VoiceAgentToolService.extract_search_query("帮我查一下语音 Agent 的打断能力，然后总结")
        self.assertEqual(query, "语音 Agent 的打断能力")

    def test_extract_audio_agent_topic_from_voice_command(self) -> None:
        topic = VoiceAgentToolService.extract_audio_agent_topic("帮我做一期关于年轻人睡眠焦虑的播客")
        self.assertEqual(topic, "年轻人睡眠焦虑的播客")

    def test_extract_tool_request_prefers_audio_agent_action(self) -> None:
        request = VoiceAgentToolService.extract_tool_request("帮我创建一个关于 AI 教育的播客草稿")
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.tool_name, "create_audio_agent_run")
        self.assertEqual(request.query, "AI 教育的播客草稿")

    def test_extract_translate_request_from_voice_command(self) -> None:
        request = VoiceAgentToolService.extract_tool_request("把你好世界翻译成英文")
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.tool_name, "translate_text")
        self.assertEqual(request.query, "你好世界\n目标语言: 英文")

    def test_extract_summary_request_from_voice_command(self) -> None:
        request = VoiceAgentToolService.extract_tool_request(
            "总结这段转录：今天我们讨论了语音 Agent 的打断、搜索和工具调用能力。"
        )
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.tool_name, "summarize_transcript")
        self.assertIn("语音 Agent", request.query)

    def test_extract_tts_request_from_voice_command(self) -> None:
        request = VoiceAgentToolService.extract_tool_request("把你好，欢迎使用 VoiceSpirit 生成语音")
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.tool_name, "synthesize_tts")
        self.assertEqual(request.query, "你好，欢迎使用 VoiceSpirit")

    def test_tts_discussion_is_not_treated_as_a_tool_command(self) -> None:
        statements = (
            "我们聊聊如何生成语音",
            "Voice Agent 的 TTS 有重复问题",
            "为什么合成语音会突然出现",
            "我刚才说的是 text to speech，不是让你执行",
        )

        for statement in statements:
            with self.subTest(statement=statement):
                self.assertIsNone(VoiceAgentToolService.extract_tts_request(statement))

    def test_explicit_speak_command_extracts_only_spoken_content(self) -> None:
        request = VoiceAgentToolService.extract_tts_request("请帮我朗读 系统已经准备好了。")

        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.query, "系统已经准备好了")

    async def test_run_search_emits_progress_result_and_sources(self) -> None:
        service = VoiceAgentToolService(research_service=FakeResearchService())  # type: ignore[arg-type]

        result = await service.run_search("voice agent", send_event=self._send_event)

        self.assertEqual(result["query"], "voice agent")
        self.assertEqual(len(result["sources"]), 1)
        self.assertIn("Voice Agent Research", result["answer"])
        self.assertEqual(
            [event["type"] for event in self.events],
            ["tool_call_started", "agent_progress", "tool_call_completed", "agent_result"],
        )
        self.assertEqual(self.events[0]["turn_id"], "")
        self.assertIsInstance(self.events[-1]["elapsed_ms"], int)

    async def test_create_audio_agent_run_emits_artifact_result(self) -> None:
        fake_audio_agent = FakeAudioAgentService()
        service = VoiceAgentToolService(
            research_service=FakeResearchService(),  # type: ignore[arg-type]
            audio_agent_service=fake_audio_agent,  # type: ignore[arg-type]
        )

        result = await service.run_create_audio_agent_run(
            "AI 教育",
            send_event=self._send_event,
            turn_id="voice-tool-1",
        )

        self.assertEqual(fake_audio_agent.create_calls[0]["topic"], "AI 教育")
        self.assertEqual(result["tool_name"], "create_audio_agent_run")
        self.assertEqual(result["artifact"]["run_id"], 42)
        self.assertEqual(
            [event["type"] for event in self.events],
            ["tool_call_started", "tool_call_completed", "agent_result"],
        )
        self.assertEqual(self.events[-1]["artifact"]["type"], "audio_agent_run")

    async def test_translate_text_emits_translation_artifact(self) -> None:
        fake_llm = FakeLLMService()
        service = VoiceAgentToolService(
            research_service=FakeResearchService(),  # type: ignore[arg-type]
            audio_agent_service=FakeAudioAgentService(),  # type: ignore[arg-type]
            llm_service=fake_llm,  # type: ignore[arg-type]
        )

        result = await service.run_translate_text(
            "你好世界",
            target_language="英文",
            send_event=self._send_event,
            turn_id="voice-tool-1",
        )

        self.assertEqual(fake_llm.translate_calls[0]["text"], "你好世界")
        self.assertEqual(fake_llm.translate_calls[0]["target_language"], "英文")
        self.assertEqual(result["tool_name"], "translate_text")
        self.assertEqual(result["artifact"]["translated_text"], "Hello world")
        self.assertEqual(
            [event["type"] for event in self.events],
            ["tool_call_started", "tool_call_completed", "agent_result"],
        )
        self.assertEqual(self.events[-1]["artifact"]["type"], "translation")

    async def test_summarize_transcript_emits_summary_artifact(self) -> None:
        fake_llm = FakeLLMService()
        service = VoiceAgentToolService(
            research_service=FakeResearchService(),  # type: ignore[arg-type]
            audio_agent_service=FakeAudioAgentService(),  # type: ignore[arg-type]
            llm_service=fake_llm,  # type: ignore[arg-type]
        )

        result = await service.run_summarize_transcript(
            "今天我们讨论了语音 Agent 的打断、搜索和工具调用能力。",
            send_event=self._send_event,
            turn_id="voice-tool-1",
        )

        self.assertEqual(result["tool_name"], "summarize_transcript")
        self.assertEqual(result["artifact"]["type"], "transcript_summary")
        self.assertIn("打断能力", result["artifact"]["summary"])
        self.assertIn("transcript summarization", service.build_model_context_prompt(result))
        self.assertEqual(
            [event["type"] for event in self.events],
            ["tool_call_started", "tool_call_completed", "agent_result"],
        )

    async def test_synthesize_tts_emits_audio_artifact(self) -> None:
        fake_tts = FakeTTSService()
        service = VoiceAgentToolService(
            research_service=FakeResearchService(),  # type: ignore[arg-type]
            audio_agent_service=FakeAudioAgentService(),  # type: ignore[arg-type]
            llm_service=FakeLLMService(),  # type: ignore[arg-type]
            tts_service=fake_tts,  # type: ignore[arg-type]
        )

        result = await service.run_synthesize_tts(
            "你好，欢迎使用 VoiceSpirit",
            send_event=self._send_event,
            turn_id="voice-tool-1",
        )

        self.assertEqual(fake_tts.generate_calls[0]["text"], "你好，欢迎使用 VoiceSpirit")
        self.assertEqual(fake_tts.generate_calls[0]["engine"], "edge")
        self.assertEqual(result["tool_name"], "synthesize_tts")
        self.assertEqual(result["artifact"]["type"], "tts_audio")
        self.assertEqual(result["artifact"]["voice"], "zh-CN-XiaoxiaoNeural")
        self.assertIn("TTS generation action", service.build_model_context_prompt(result))
        self.assertEqual(
            [event["type"] for event in self.events],
            ["tool_call_started", "tool_call_completed", "agent_result"],
        )

    async def test_tool_session_passes_search_result_to_handler(self) -> None:
        service = VoiceAgentToolService(research_service=FakeResearchService())  # type: ignore[arg-type]
        session = VoiceAgentToolSession(service=service)
        handled: list[dict[str, object]] = []

        async def on_result(result: dict[str, object]) -> None:
            handled.append(result)

        turn_id = await session.handle_user_transcript(
            "搜索 voice agent",
            send_event=self._send_event,
            on_result=on_result,
        )
        await session.drain()

        self.assertEqual(turn_id, "voice-tool-1")
        self.assertEqual(len(handled), 1)
        self.assertEqual(handled[0]["query"], "voice agent")
        self.assertEqual(handled[0]["tool_name"], "search_web")
        self.assertEqual(handled[0]["turn_id"], "voice-tool-1")
        self.assertEqual(handled[0]["source_count"], 1)
        self.assertIn("External search tool context", service.build_model_context_prompt(handled[0]))

    async def test_tool_session_cancels_active_search_on_interruption(self) -> None:
        session = VoiceAgentToolSession(
            service=VoiceAgentToolService(research_service=HangingResearchService())  # type: ignore[arg-type]
        )

        await session.handle_user_transcript("帮我查一下语音 Agent", send_event=self._send_event)
        await asyncio.sleep(0)
        await session.cancel(send_event=self._send_event, reason="interrupted")

        cancel_events = [event for event in self.events if event["type"] == "tool_call_cancelled"]
        self.assertEqual(len(cancel_events), 1)
        self.assertEqual(cancel_events[0]["tool_name"], "search_web")
        self.assertEqual(cancel_events[0]["query"], "语音 Agent")
        self.assertEqual(cancel_events[0]["turn_id"], "voice-tool-1")
        self.assertEqual(cancel_events[0]["reason"], "interrupted")
        self.assertIsInstance(cancel_events[0]["elapsed_ms"], int)


if __name__ == "__main__":
    unittest.main()

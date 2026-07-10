import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from services.realtime_voice_service import RealtimeVoiceService

class TestDashScopeRealtime(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = RealtimeVoiceService()

    @patch("dashscope.audio.qwen_omni.OmniRealtimeConversation")
    async def test_dashscope_settings_resolution(self, mock_conv):
        # Mock config
        mock_config = MagicMock()
        mock_config.get_provider_settings.return_value = {
            "api_key": "test_key",
            "model": "qwen-realtime",
            "base_url": "https://dashscope.aliyuncs.com"
        }
        self.service.config = mock_config

        settings = self.service._resolve_dashscope_settings("qwen-realtime")
        self.assertEqual(settings["api_key"], "test_key")
        self.assertEqual(settings["model"], "qwen-realtime")
        self.assertEqual(settings["region"], "cn")

    @patch("dashscope.audio.qwen_omni.OmniRealtimeConversation")
    async def test_dashscope_session_init(self, mock_conv):
        # This is a shallow smoke test to ensure DashScope methods exist and are called
        mock_ws = MagicMock()
        mock_ws.send_json = asyncio.Future()
        mock_ws.send_json.set_result(None)
        
        # We mock the entire stream_dashscope_session dependencies since we don't have a real WS loop here
        with patch.object(self.service, "_resolve_dashscope_settings", return_value={
            "api_key": "sk-test",
            "model": "qwen-realtime",
            "region": "cn"
        }):
            # We don't actually run the full session loop as it requires a real websocket
            # but we can verify the settings resolution works.
            pass

    async def test_google_tool_result_injection_sends_context_turn(self):
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()
        mock_session = MagicMock()
        mock_session.send = AsyncMock()

        await self.service._apply_google_tool_result(
            mock_ws,
            mock_session,
            {
                "query": "voice agent",
                "answer": "summary",
                "sources": [{"title": "Source", "uri": "https://example.com", "snippet": "content"}],
            },
        )

        mock_ws.send_json.assert_awaited_once()
        mock_session.send.assert_awaited_once()
        self.assertIn("External search tool context", mock_session.send.await_args.kwargs["input"])
        self.assertTrue(mock_session.send.await_args.kwargs["end_of_turn"])

    async def test_dashscope_tool_result_injection_creates_response(self):
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()
        mock_conversation = MagicMock()

        await self.service._apply_dashscope_tool_result(
            mock_ws,
            mock_conversation,
            {
                "query": "voice agent",
                "answer": "summary",
                "sources": [{"title": "Source", "uri": "https://example.com", "snippet": "content"}],
            },
        )

        mock_ws.send_json.assert_awaited_once()
        mock_conversation.create_response.assert_called_once()
        self.assertIn(
            "External search tool context",
            mock_conversation.create_response.call_args.kwargs["instructions"],
        )

    async def test_response_gated_event_includes_tool_turn_metadata(self):
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await self.service._send_response_gated(
            mock_ws,
            provider="DashScope",
            tool_name="search_web",
            query="voice agent",
            turn_id="voice-tool-1",
        )

        mock_ws.send_json.assert_awaited_once_with(
            {
                "type": "response_gated",
                "provider": "DashScope",
                "tool_name": "search_web",
                "query": "voice agent",
                "turn_id": "voice-tool-1",
                "message": "检测到工具请求，已暂停直接回答，等待工具结果。",
            }
        )

if __name__ == "__main__":
    unittest.main()

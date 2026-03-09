from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.desktop_memory import DesktopMemoryManager


class FakeConfigManager:
    def __init__(self, values: dict[str, object] | None = None):
        self.values = values or {}

    def get(self, key: str, default=None):
        return self.values.get(key, default)

    def get_config_path(self) -> str:
        return str(ROOT / "config.json")


class DesktopMemoryManagerTests(unittest.TestCase):
    def make_manager(self, **overrides: object) -> DesktopMemoryManager:
        values = {
            "memory_settings.enabled": True,
            "memory_settings.api_key": "test-key",
            "memory_settings.remember_chat": True,
            "memory_settings.remember_voice_chat": True,
            "memory_settings.remember_recordings": False,
            "memory_settings.store_transcript_fulltext": False,
            **overrides,
        }
        return DesktopMemoryManager(FakeConfigManager(values))

    def test_extracts_voice_preference(self) -> None:
        manager = self.make_manager()

        entries = manager._extract_memory_entries(
            "以后默认用 Xiaoxiao，语速慢一点。",
            source="chat_text",
        )

        self.assertIn("语音偏好: 以后默认用 Xiaoxiao", entries)
        self.assertIn("语音偏好: 语速慢一点", entries)

    def test_extracts_action_and_constraint(self) -> None:
        manager = self.make_manager()

        entries = manager._extract_memory_entries(
            "接下来先完成桌面端 Memory Center，不要改 desktop_memory.py。",
            source="chat_text",
        )

        self.assertIn("待办事项: 接下来先完成桌面端 Memory Center", entries)
        self.assertIn("约束条件: 不要改 desktop_memory.py", entries)

    def test_extracts_explicit_summary(self) -> None:
        manager = self.make_manager()

        entries = manager._extract_memory_entries(
            "总结一下，这次主要把桌面端记忆设置接到后端配置层。",
            source="chat_text",
        )

        self.assertEqual(entries, ["会话摘要: 这次主要把桌面端记忆设置接到后端配置层"])

    def test_prefers_action_over_overlapping_summary(self) -> None:
        manager = self.make_manager()

        entries = manager._extract_memory_entries(
            "总结一下，这次主要修复桌面端设置页，接下来补 Memory Center。",
            source="chat_text",
        )

        self.assertIn("待办事项: 接下来补 Memory Center", entries)
        self.assertFalse(any(item.startswith("会话摘要:") for item in entries))

    def test_extracts_stable_task_context(self) -> None:
        manager = self.make_manager()

        entries = manager._extract_memory_entries(
            "当前在做 VoiceSpirit 桌面端记忆接入，主要在收紧 transcript 提炼策略。",
            source="chat_text",
        )

        self.assertIn("当前任务上下文: 当前在做 VoiceSpirit 桌面端记忆接入", entries)
        self.assertIn("当前任务上下文: 主要在收紧 transcript 提炼策略", entries)

    def test_ignores_questions(self) -> None:
        manager = self.make_manager()

        entries = manager._extract_memory_entries(
            "为什么另外一个窗口的 WSL Codex 不回复？",
            source="chat_text",
        )

        self.assertEqual(entries, [])

    def test_fulltext_fallback_only_for_voice_sources(self) -> None:
        manager = self.make_manager(**{"memory_settings.store_transcript_fulltext": True})

        voice_entries = manager._extract_memory_entries(
            "今天会议里大家都在同步项目进度。",
            source="recording_transcription",
        )
        chat_entries = manager._extract_memory_entries(
            "今天会议里大家都在同步项目进度。",
            source="chat_text",
        )

        self.assertEqual(voice_entries, ["语音输入记录: 今天会议里大家都在同步项目进度。"])
        self.assertEqual(chat_entries, [])

    def test_dedupes_recent_memory_entries_across_turns(self) -> None:
        manager = self.make_manager()
        entries = ["语音偏好: 以后默认用 Xiaoxiao"]

        with patch("app.core.desktop_memory.time.monotonic", side_effect=[100.0, 120.0, 800.0]):
            first = manager._filter_recent_memory_entries(entries)
            second = manager._filter_recent_memory_entries(entries)
            third = manager._filter_recent_memory_entries(entries)

        self.assertEqual(first, entries)
        self.assertEqual(second, [])
        self.assertEqual(third, entries)

    def test_deduping_keeps_distinct_entries(self) -> None:
        manager = self.make_manager()

        with patch("app.core.desktop_memory.time.monotonic", side_effect=[100.0]):
            kept = manager._filter_recent_memory_entries(
                [
                    "语音偏好: 以后默认用 Xiaoxiao",
                    "待办事项: 接下来补 Memory Center",
                ]
            )

        self.assertEqual(
            kept,
            [
                "语音偏好: 以后默认用 Xiaoxiao",
                "待办事项: 接下来补 Memory Center",
            ],
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import threading
import time

from backend.services.evermem_service import EverMemService

logger = logging.getLogger(__name__)


class DesktopMemoryManager:
    """Applies lightweight memory policy for desktop voice workflows."""

    _PREFERENCE_PATTERNS = (
        r"喜欢",
        r"偏好",
        r"默认",
        r"请用",
        r"以后",
        r"尽量",
        r"不要",
        r"别用",
        r"记住",
        r"prefer",
        r"default",
        r"always",
        r"usually",
    )
    _PREFERENCE_ACTION_PATTERNS = (
        r"请用",
        r"用",
        r"使用",
        r"保持",
        r"改成",
        r"切换到",
        r"prefer",
        r"default to",
        r"always use",
        r"usually use",
    )
    _VOICE_PATTERNS = (
        r"音色",
        r"语速",
        r"播客",
        r"朗读",
        r"配音",
        r"男声",
        r"女声",
        r"voice",
        r"rate",
        r"host",
        r"guest",
    )
    _VOICE_VALUE_PATTERNS = (
        r"xiaoxiao",
        r"xiaoyi",
        r"jenny",
        r"alloy",
        r"echo",
        r"nova",
        r"shimmer",
        r"verse",
        r"zephyr",
        r"cherry",
        r"neural",
        r"男声",
        r"女声",
        r"快一点",
        r"慢一点",
    )
    _VOICE_PREFERENCE_PATTERNS = (
        r"请用",
        r"用",
        r"使用",
        r"改成",
        r"切换到",
        r"男声",
        r"女声",
        r"快一点",
        r"慢一点",
    )
    _TASK_PATTERNS = (
        r"任务",
        r"待办",
        r"项目",
        r"计划",
        r"安排",
        r"需求",
        r"继续",
        r"今天",
        r"明天",
        r"deadline",
        r"todo",
        r"next step",
        r"milestone",
        r"release",
        r"ship",
    )
    _TASK_CONTEXT_PATTERNS = (
        r"当前在做",
        r"现在在做",
        r"最近在做",
        r"主要在做",
        r"主要在",
        r"正在",
        r"项目是",
        r"项目叫",
        r"主题是",
        r"负责",
        r"聚焦",
        r"focus on",
        r"working on",
        r"current project",
    )
    _TASK_ACTION_PATTERNS = (
        r"先",
        r"需要",
        r"记得",
        r"继续",
        r"接下来",
        r"下一步",
        r"安排",
        r"计划",
        r"完成",
        r"推进",
        r"实现",
        r"修复",
        r"上线",
        r"发布",
        r"整理",
        r"记录",
        r"todo",
        r"next step",
        r"follow up",
        r"ship",
    )
    _ACTION_ITEM_PATTERNS = (
        r"待办",
        r"todo",
        r"接下来",
        r"下一步",
        r"先",
        r"然后",
        r"需要",
        r"记得",
        r"follow up",
        r"action item",
    )
    _CONSTRAINT_PATTERNS = (
        r"不要",
        r"别",
        r"不能",
        r"必须",
        r"只能",
        r"限制",
        r"约束",
        r"截至",
        r"截止",
        r"deadline",
        r"do not",
        r"must",
        r"must not",
        r"avoid",
    )
    _SUMMARY_PATTERNS = (
        r"^总结",
        r"^结论",
        r"^本次",
        r"^这次",
        r"^核心是",
        r"^主要是",
        r"summary",
        r"in short",
    )
    _QUESTION_PATTERNS = (
        r"\?$",
        r"？$",
        r"^(什么|怎么|为啥|为什么|是否|能不能|可不可以)",
        r"^(what|why|how|should|can|could)\b",
        r"(吗|呢)[\s。！？!?]*$",
    )
    _VOICE_SOURCES = {"live_transcript", "recording_transcription"}
    _RECENT_MEMORY_WINDOW_SECONDS = 600
    _RECENT_MEMORY_MAX_ENTRIES = 64
    _MEMORY_LABELS = {
        "voice_preference": "语音偏好",
        "user_preference": "用户偏好",
        "constraint": "约束条件",
        "action_item": "待办事项",
        "task_context": "当前任务上下文",
        "session_summary": "会话摘要",
    }

    def __init__(self, config_manager, db_manager=None):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self._recent_memory_entries: dict[str, float] = {}
        self._recent_memory_lock = threading.Lock()

    def capture_voice_transcript(
        self,
        *,
        session_id: int | None,
        text: str,
        source: str,
        provider: str = "",
        model: str = "",
    ) -> None:
        cleaned = self._clean_text(text)
        if not cleaned:
            return

        self._store_transcript_asset(
            session_id=session_id,
            text=cleaned,
            source=source,
            provider=provider,
            model=model,
        )

        if not self._memory_enabled() or self._temporary_session_enabled():
            return

        if source == "recording_transcription" and not self._setting_bool("remember_recordings", False):
            return
        if source == "live_transcript" and not self._setting_bool("remember_voice_chat", True):
            return

        memory_entries = self._extract_memory_entries(cleaned, source=source)
        for content in self._filter_recent_memory_entries(memory_entries):
            self._enqueue_memory_write(content=content, source=source)

    def capture_chat_message(
        self,
        *,
        text: str,
        source: str = "chat_text",
    ) -> None:
        cleaned = self._clean_text(text)
        if not cleaned:
            return

        if not self._memory_enabled() or self._temporary_session_enabled():
            return
        if not self._setting_bool("remember_chat", True):
            return

        memory_entries = self._extract_memory_entries(cleaned, source=source)
        for content in self._filter_recent_memory_entries(memory_entries):
            self._enqueue_memory_write(content=content, source=source)

    def _store_transcript_asset(
        self,
        *,
        session_id: int | None,
        text: str,
        source: str,
        provider: str,
        model: str,
    ) -> None:
        if not self.db_manager or session_id is None:
            return
        try:
            self.db_manager.add_voice_transcript(
                session_id,
                source,
                text,
                provider=provider,
                model=model,
            )
        except Exception:
            logger.exception("Failed to store voice transcript asset")

    def _extract_memory_entries(self, text: str, *, source: str) -> list[str]:
        entries: list[str] = []
        for item in self._extract_structured_items(text):
            label = self._MEMORY_LABELS.get(item["kind"])
            if not label:
                continue
            entries.append(f"{label}: {item['content']}")

        if not entries and source in self._VOICE_SOURCES and self._setting_bool("store_transcript_fulltext", False):
            entries.append(f"语音输入记录: {self._compact_text(text)}")

        return entries[:3]

    def _filter_recent_memory_entries(self, entries: list[str]) -> list[str]:
        if not entries:
            return entries

        kept: list[str] = []
        now = self._now()
        with self._recent_memory_lock:
            self._prune_recent_memory_entries(now)
            for entry in entries:
                key = self._recent_memory_key(entry)
                seen_at = self._recent_memory_entries.get(key)
                if seen_at is not None and (now - seen_at) < self._RECENT_MEMORY_WINDOW_SECONDS:
                    continue
                self._recent_memory_entries[key] = now
                kept.append(entry)
            self._prune_recent_memory_entries(now)
        return kept

    def _extract_structured_items(self, text: str) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for sentence in self._split_sentences(text):
            candidate = self._normalize_candidate(sentence)
            if not candidate or self._looks_like_question(candidate):
                continue

            kind = self._classify_candidate(candidate)
            if not kind:
                continue

            dedupe_key = (kind, candidate.lower())
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            items.append({"kind": kind, "content": candidate})

        items = self._post_process_items(items)
        items.sort(key=lambda item: (-self._memory_priority(item["kind"]), len(item["content"])))
        return items[:3]

    def _classify_candidate(self, text: str) -> str | None:
        has_preference = self._matches_any(text, self._PREFERENCE_PATTERNS)
        has_voice = self._matches_any(text, self._VOICE_PATTERNS) or self._matches_any(
            text, self._VOICE_VALUE_PATTERNS
        )
        has_constraint = self._matches_any(text, self._CONSTRAINT_PATTERNS)
        has_action = self._matches_any(text, self._ACTION_ITEM_PATTERNS)
        has_task = self._matches_any(text, self._TASK_PATTERNS) and self._matches_any(
            text, self._TASK_ACTION_PATTERNS
        )
        has_task_context = self._matches_any(text, self._TASK_CONTEXT_PATTERNS)
        has_summary = self._matches_any(text, self._SUMMARY_PATTERNS)

        if has_voice and (has_preference or self._matches_any(text, self._VOICE_PREFERENCE_PATTERNS)):
            return "voice_preference"
        if has_preference and self._matches_any(text, self._PREFERENCE_ACTION_PATTERNS):
            return "user_preference"
        if has_constraint and not has_voice:
            return "constraint"
        if has_action and (has_task or len(text) >= 12):
            return "action_item"
        if has_task_context or (has_task and not has_summary):
            return "task_context"
        if has_summary and len(text) >= 12:
            return "session_summary"
        return None

    @staticmethod
    def _post_process_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
        if not items:
            return items

        kinds = {item["kind"] for item in items}
        filtered = list(items)

        if "session_summary" in kinds and ("action_item" in kinds or "constraint" in kinds):
            filtered = [item for item in filtered if item["kind"] != "session_summary"]

        if "action_item" in kinds and "task_context" in kinds:
            filtered = [
                item
                for item in filtered
                if not (
                    item["kind"] == "task_context"
                    and any(
                        other["kind"] == "action_item" and other["content"] in item["content"]
                        for other in filtered
                    )
                )
            ]

        return filtered

    def _normalize_candidate(self, text: str) -> str:
        compact = self._compact_text(text)
        compact = re.sub(r"^[,.;:，。；：、\-\s]+", "", compact)
        compact = re.sub(
            r"^(我觉得|我想|我希望|那个|就是|嗯|呃|请帮我|帮我|麻烦你|总结一下|简单说|结论是)\s*",
            "",
            compact,
            flags=re.IGNORECASE,
        )
        compact = re.sub(r"\s+", " ", compact).strip()
        if len(compact) < 4:
            return ""
        return compact[:160]

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts: list[str] = []
        for segment in re.split(r"[。！？!?\n;；]+", text):
            if not segment.strip():
                continue
            clauses = [item.strip() for item in re.split(r"[，,]+", segment) if item.strip()]
            parts.extend(clauses or [segment.strip()])
        return parts

    def _looks_like_question(self, text: str) -> bool:
        return self._matches_any(text, self._QUESTION_PATTERNS)

    @staticmethod
    def _memory_priority(kind: str) -> int:
        priority = {
            "voice_preference": 3,
            "user_preference": 3,
            "constraint": 2,
            "action_item": 2,
            "task_context": 1,
            "session_summary": 0,
        }
        return priority.get(kind, 0)

    def _prune_recent_memory_entries(self, now: float) -> None:
        expired_keys = [
            key
            for key, seen_at in self._recent_memory_entries.items()
            if (now - seen_at) >= self._RECENT_MEMORY_WINDOW_SECONDS
        ]
        for key in expired_keys:
            self._recent_memory_entries.pop(key, None)

        if len(self._recent_memory_entries) <= self._RECENT_MEMORY_MAX_ENTRIES:
            return

        for key, _ in sorted(self._recent_memory_entries.items(), key=lambda item: item[1])[
            : len(self._recent_memory_entries) - self._RECENT_MEMORY_MAX_ENTRIES
        ]:
            self._recent_memory_entries.pop(key, None)

    @staticmethod
    def _recent_memory_key(entry: str) -> str:
        return re.sub(r"\s+", " ", entry).strip().lower()

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def _enqueue_memory_write(self, *, content: str, source: str) -> None:
        api_key = self._setting_str("api_key")
        if not api_key:
            return

        thread = threading.Thread(
            target=self._write_memory_sync,
            kwargs={"content": content, "source": source},
            daemon=True,
        )
        thread.start()

    def _write_memory_sync(self, *, content: str, source: str) -> None:
        async def runner() -> None:
            service = EverMemService(
                api_url=self._setting_str("api_url", "https://api.evermind.ai"),
                api_key=self._setting_str("api_key"),
            )
            await service.add_memory(
                content=content,
                user_id=self._scope_id(),
                sender=f"{self._scope_id()}_{source}",
                sender_name="VoiceSpirit Desktop",
            )

        try:
            asyncio.run(runner())
        except Exception:
            logger.exception("Failed to write desktop memory")

    def _scope_id(self) -> str:
        explicit = self._setting_str("scope_id")
        if explicit:
            return explicit
        config_path = self.config_manager.get_config_path()
        digest = hashlib.sha256(config_path.encode("utf-8")).hexdigest()[:24]
        return f"desktop_{digest}"

    def _memory_enabled(self) -> bool:
        return self._setting_bool("enabled", False)

    def _temporary_session_enabled(self) -> bool:
        return self._setting_bool("temporary_session", False)

    def _setting_bool(self, key: str, default: bool) -> bool:
        value = self.config_manager.get(f"memory_settings.{key}", default)
        return bool(value)

    def _setting_str(self, key: str, default: str = "") -> str:
        return str(self.config_manager.get(f"memory_settings.{key}", default) or "").strip()

    @staticmethod
    def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = str(text or "").strip()
        if not cleaned or cleaned in {"[🎤 语音输入]", "[语音输入]"}:
            return ""
        return cleaned

    @staticmethod
    def _compact_text(text: str) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        return compact[:280]

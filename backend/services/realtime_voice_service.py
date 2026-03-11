from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

print(f"DEBUG: Realtime service using Python: {sys.executable}")
print(f"DEBUG: Python Path: {sys.path}")

logger = logging.getLogger(__name__)

from .config_loader import BackendConfig
from .evermem_config import EverMemConfig

try:
    from google import genai
    from google.genai import types
except ImportError as e:  # pragma: no cover - validated at runtime in deployed env
    print(f"DEBUG: Google GenAI Import Error: {e}")
    genai = None
    types = None
except Exception as e:
    print(f"DEBUG: Google GenAI Unexpected Error: {e}")
    genai = None
    types = None

try:
    from dashscope.audio.qwen_omni import AudioFormat, MultiModality, OmniRealtimeConversation
except ImportError as e:  # pragma: no cover - validated at runtime in deployed env
    print(f"DEBUG: DashScope Realtime Import Error: {e}")
    AudioFormat = None
    MultiModality = None
    OmniRealtimeConversation = None
except Exception as e:
    print(f"DEBUG: DashScope Realtime Unexpected Error: {e}")
    AudioFormat = None
    MultiModality = None
    OmniRealtimeConversation = None


DEFAULT_GOOGLE_REALTIME_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_GOOGLE_REALTIME_VOICE = "Puck"
DEFAULT_DASHSCOPE_REALTIME_MODEL = "qwen3-omni-flash-realtime-2025-12-01"
DEFAULT_DASHSCOPE_REALTIME_VOICE = "Cherry"
BASE_REALTIME_INSTRUCTIONS = (
    "You are a helpful, friendly, and intelligent AI assistant. "
    "Respond naturally and conversationally in the same language the user speaks."
)


def _resolve_pending_cache_path() -> Path:
    app_name = "VoiceSpirit"
    if os.name == "nt":
        base_dir = Path(os.environ.get("APPDATA", str(Path.cwd())))
        preferred_dir = base_dir / app_name
    else:
        xdg_state_home = os.environ.get("XDG_STATE_HOME")
        base_dir = Path(xdg_state_home) if xdg_state_home else Path.home() / ".local" / "state"
        preferred_dir = base_dir / app_name

    fallback_dir = Path.cwd() / ".voicespirit-state" / app_name
    for candidate in (preferred_dir, fallback_dir):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate / "realtime_pending_memory.json"
        except OSError:
            continue

    return fallback_dir / "realtime_pending_memory.json"


def _merge_memory_text(previous: str, incoming: str) -> str:
    next_text = str(incoming or "").strip()
    if not next_text:
        return previous
    if not previous:
        return next_text
    if next_text.startswith(previous):
        return next_text
    if previous.endswith(next_text):
        return previous
    return f"{previous}{next_text}"


class RealtimeMemorySession:
    _PREFERENCE_PATTERNS = (
        r"喜欢",
        r"偏好",
        r"默认",
        r"以后",
        r"尽量",
        r"不要",
        r"记住",
        r"prefer",
        r"default",
        r"always",
    )
    _PREFERENCE_ACTION_PATTERNS = (
        r"请用",
        r"用",
        r"使用",
        r"改成",
        r"切换到",
        r"保持",
        r"prefer",
        r"default to",
        r"always use",
    )
    _VOICE_PATTERNS = (
        r"音色",
        r"声音",
        r"语速",
        r"播客",
        r"朗读",
        r"配音",
        r"男声",
        r"女声",
        r"voice",
        r"rate",
    )
    _TASK_PATTERNS = (
        r"任务",
        r"待办",
        r"项目",
        r"计划",
        r"安排",
        r"需求",
        r"工作",
        r"重点",
        r"继续",
        r"今天",
        r"明天",
        r"deadline",
        r"todo",
        r"next step",
        r"milestone",
        r"比赛",
        r"提交",
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
        r"修复",
        r"上线",
        r"发布",
        r"准备",
        r"提交",
        r"todo",
        r"next step",
    )
    _TASK_CONTEXT_PATTERNS = (
        r"当前在做",
        r"现在在做",
        r"最近在做",
        r"主要在做",
        r"主要是",
        r"正在",
        r"项目是",
        r"主题是",
        r"负责",
        r"focus on",
        r"working on",
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
        r"must",
        r"avoid",
    )
    _SUMMARY_PATTERNS = (
        r"^总结",
        r"^结论",
        r"^本次",
        r"^这次",
        r"^核心",
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
    _MEMORY_LABELS = {
        "voice_preference": "语音偏好",
        "user_preference": "用户偏好",
        "constraint": "约束条件",
        "action_item": "待办事项",
        "task_context": "当前任务上下文",
        "session_summary": "会话摘要",
    }
    _RETRIEVE_HINT_PATTERNS = (
        r"之前",
        r"上次",
        r"刚才",
        r"刚刚",
        r"继续",
        r"还是",
        r"沿用",
        r"默认",
        r"记得",
        r"你还记得",
        r"previous",
        r"earlier",
        r"before",
        r"continue",
        r"still",
        r"same",
        r"remember",
        r"检索",
        r"搜索",
        r"回忆",
        r"想起",
        r"提到",
        r"刚才说",
        r"重点工作",
    )
    _RETRIEVE_TIMEOUT_SECONDS = 0.12
    _FORCED_RETRIEVE_TIMEOUT_SECONDS = 0.35
    _PENDING_MEMORY_TTL_SECONDS = 1800
    _PENDING_MEMORY_MAX_PER_SCOPE = 24
    _PENDING_MEMORY_CACHE: dict[str, list[dict[str, Any]]] = {}
    _PENDING_CACHE_PATH: Path = _resolve_pending_cache_path()

    def __init__(self) -> None:
        self._config = EverMemConfig()
        self._current_user_text = ""
        self._current_assistant_text = ""
        self._pending_tasks: set[asyncio.Task[None]] = set()
        self._last_retrieved_query = ""
        self._last_memory_context = ""
        self._last_memory_count = 0
        self._last_local_pending_count = 0
        self._last_cloud_count = 0
        self._last_retrieve_attempted = False

    def configure(self, payload: dict[str, Any] | None) -> None:
        if not isinstance(payload, dict) or not payload.get("enabled"):
            self._config = EverMemConfig()
            self._current_user_text = ""
            self._current_assistant_text = ""
            logger.info("voice_memory_config disabled")
            return

        self._config.update_from_headers(
            {
                "X-EverMem-Enabled": "true",
                "X-EverMem-Url": payload.get("api_url", ""),
                "X-EverMem-Key": payload.get("api_key", ""),
                "X-EverMem-Scope": payload.get("scope_id", ""),
            }
        )
        logger.info(
            "voice_memory_config enabled scope=%s url=%s",
            self._config.memory_scope,
            self._config.url,
        )

    def note_user_transcript(self, text: str) -> None:
        cleaned = str(text or "").strip()
        if cleaned != self._current_user_text:
            self._last_retrieved_query = ""
            self._last_memory_context = ""
            self._last_memory_count = 0
            self._last_local_pending_count = 0
            self._last_cloud_count = 0
            self._last_retrieve_attempted = False
        self._current_user_text = cleaned

    def note_assistant_text(self, text: str) -> None:
        self._current_assistant_text = _merge_memory_text(self._current_assistant_text, text)

    async def flush_turn(self) -> dict[str, Any]:
        service = self._config.get_service()
        user_text = self._current_user_text.strip()
        self._current_user_text = ""
        self._current_assistant_text = ""

        if not service or not user_text:
            logger.info(
                "voice_memory_write skipped reason=%s scope=%s text=%r",
                "disabled_or_empty",
                self._config.memory_scope,
                user_text[:120],
            )
            return {
                "enabled": bool(service),
                "attempted_count": 0,
                "saved_count": 0,
                "failed_count": 0,
                "reason": "disabled_or_empty",
            }

        memory_entries = self._extract_memory_entries(user_text)
        if not memory_entries:
            logger.info(
                "voice_memory_write skipped reason=%s scope=%s text=%r",
                "no_candidate_memory",
                self._config.memory_scope,
                user_text[:120],
            )
            return {
                "enabled": True,
                "attempted_count": 0,
                "saved_count": 0,
                "failed_count": 0,
                "reason": "no_candidate_memory",
            }

        queued_count = self._queue_pending_entries(self._config.memory_scope, memory_entries)
        result = await self._persist_entries(entries=memory_entries)
        result["enabled"] = True
        result["local_pending_count"] = queued_count
        logger.info(
            "voice_memory_write scope=%s attempted=%s saved=%s failed=%s local_pending=%s entries=%s",
            self._config.memory_scope,
            result.get("attempted_count", 0),
            result.get("saved_count", 0),
            result.get("failed_count", 0),
            queued_count,
            memory_entries,
        )
        return result

    async def drain(self) -> None:
        if not self._pending_tasks:
            return
        await asyncio.gather(*list(self._pending_tasks), return_exceptions=True)

    async def _persist_entries(self, *, entries: list[str]) -> dict[str, int]:
        service = self._config.get_service()
        if not service or not entries:
            return {"attempted_count": 0, "saved_count": 0, "failed_count": 0}

        scope = self._config.memory_scope
        saved_count = 0
        failed_count = 0
        for entry in entries:
            try:
                result = await service.add_memory(
                    content=entry,
                    user_id=scope,
                    sender=scope,
                    sender_name="User",
                )
                if result:
                    saved_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1
        return {
            "attempted_count": len(entries),
            "saved_count": saved_count,
            "failed_count": failed_count,
        }

    def should_retrieve_context(self, text: str | None = None) -> bool:
        service = self._config.get_service()
        candidate = str(text or self._current_user_text or "").strip()
        if not service or not candidate:
            logger.info(
                "voice_memory_retrieve skipped reason=%s scope=%s query=%r",
                "disabled_or_empty",
                self._config.memory_scope,
                candidate[:120],
            )
            return False
        if service.should_skip_memory(candidate):
            logger.info(
                "voice_memory_retrieve skipped reason=%s scope=%s query=%r",
                "trivial_message",
                self._config.memory_scope,
                candidate[:120],
            )
            return False
        if self._matches_any(candidate, self._RETRIEVE_HINT_PATTERNS):
            logger.info(
                "voice_memory_retrieve trigger=hint scope=%s query=%r",
                self._config.memory_scope,
                candidate[:120],
            )
            return True

        for sentence in self._split_sentences(candidate):
            normalized = self._normalize_candidate(sentence)
            if not normalized:
                continue
            kind = self._classify_candidate(normalized)
            if kind in {"voice_preference", "user_preference", "constraint", "action_item", "task_context"}:
                logger.info(
                    "voice_memory_retrieve trigger=classified kind=%s scope=%s query=%r",
                    kind,
                    self._config.memory_scope,
                    candidate[:120],
                )
                return True

        if self._looks_like_question(candidate):
            question_targets_memory = (
                self._matches_any(candidate, self._TASK_PATTERNS)
                or self._matches_any(candidate, self._VOICE_PATTERNS)
                or self._matches_any(candidate, self._PREFERENCE_PATTERNS)
                or self._matches_any(candidate, self._CONSTRAINT_PATTERNS)
            )
            if question_targets_memory and len(candidate) >= 8:
                logger.info(
                    "voice_memory_retrieve trigger=question_target scope=%s query=%r",
                    self._config.memory_scope,
                    candidate[:120],
                )
                return True
            logger.info(
                "voice_memory_retrieve skipped reason=%s scope=%s query=%r",
                "question_without_memory_target",
                self._config.memory_scope,
                candidate[:120],
            )
            return False
        logger.info(
            "voice_memory_retrieve trigger=length scope=%s query=%r",
            self._config.memory_scope,
            candidate[:120],
        )
        return len(candidate) >= 18

    def is_forced_recall_query(self, text: str | None = None) -> bool:
        candidate = str(text or self._current_user_text or "").strip()
        if not candidate:
            return False
        if not self._looks_like_question(candidate):
            return False
        return self._matches_any(candidate, self._RETRIEVE_HINT_PATTERNS)

    async def retrieve_memory_context(self) -> dict[str, Any]:
        service = self._config.get_service()
        query = self._current_user_text.strip()
        if not service or not query or not self.should_retrieve_context(query):
            return {
                "context": "",
                "memories_retrieved": 0,
                "local_pending_count": 0,
                "cloud_count": 0,
                "attempted": False,
            }
        if query == self._last_retrieved_query:
            logger.info(
                "voice_memory_retrieve cache_hit scope=%s count=%s query=%r",
                self._config.memory_scope,
                self._last_memory_count,
                query[:120],
            )
            return {
                "context": self._last_memory_context,
                "memories_retrieved": self._last_memory_count,
                "local_pending_count": self._last_local_pending_count,
                "cloud_count": self._last_cloud_count,
                "attempted": self._last_retrieve_attempted,
            }

        local_memories = self._search_pending_entries(self._config.memory_scope, query)

        try:
            timeout_seconds = (
                self._FORCED_RETRIEVE_TIMEOUT_SECONDS
                if self.is_forced_recall_query(query)
                else self._RETRIEVE_TIMEOUT_SECONDS
            )
            memories = await asyncio.wait_for(
                service.search_memories(
                    query=query,
                    user_id=self._config.memory_scope,
                    memory_types=["episodic_memory", "profile"],
                    min_score=0.35,
                ),
                timeout=timeout_seconds,
            )
        except Exception:
            logger.exception(
                "voice_memory_retrieve error scope=%s query=%r",
                self._config.memory_scope,
                query[:120],
            )
            memories = []

        combined = self._merge_retrieved_memories(local_memories=local_memories, cloud_memories=memories)
        lines: list[str] = []
        local_count = len(local_memories)
        cloud_count = len(memories)
        for idx, memory in enumerate(combined[:3], start=1):
            content = str(memory.get("content", "")).strip()
            if not content:
                continue
            source = str(memory.get("source", "")).strip()
            if source == "local_pending":
                lines.append(f"{idx}. [本地待同步记忆] {content[:180]}")
            else:
                lines.append(f"{idx}. [云端长期记忆] {content[:180]}")

        self._last_retrieved_query = query
        self._last_memory_context = "\n".join(lines)
        self._last_memory_count = len(lines)
        self._last_local_pending_count = local_count
        self._last_cloud_count = cloud_count
        self._last_retrieve_attempted = True
        logger.info(
            "voice_memory_retrieve result scope=%s count=%s local_pending=%s cloud=%s query=%r",
            self._config.memory_scope,
            self._last_memory_count,
            local_count,
            cloud_count,
            query[:120],
        )
        return {
            "context": self._last_memory_context,
            "memories_retrieved": self._last_memory_count,
            "local_pending_count": local_count,
            "cloud_count": cloud_count,
            "attempted": True,
        }

    def _extract_memory_entries(self, text: str) -> list[str]:
        entries: list[str] = []
        seen: set[str] = set()

        for sentence in self._split_sentences(text):
            candidate = self._normalize_candidate(sentence)
            if not candidate or self._looks_like_question(candidate):
                continue

            kind = self._classify_candidate(candidate)
            if not kind:
                continue

            labeled = f"{self._MEMORY_LABELS[kind]}: {candidate}"
            dedupe_key = labeled.lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            entries.append(labeled)

        return entries[:2]

    def _classify_candidate(self, text: str) -> str | None:
        has_preference = self._matches_any(text, self._PREFERENCE_PATTERNS)
        has_voice = self._matches_any(text, self._VOICE_PATTERNS)
        has_constraint = self._matches_any(text, self._CONSTRAINT_PATTERNS)
        has_task = self._matches_any(text, self._TASK_PATTERNS)
        has_task_action = self._matches_any(text, self._TASK_ACTION_PATTERNS)
        has_task_context = self._matches_any(text, self._TASK_CONTEXT_PATTERNS)
        has_summary = self._matches_any(text, self._SUMMARY_PATTERNS)

        if has_voice and has_preference:
            return "voice_preference"
        if has_preference and self._matches_any(text, self._PREFERENCE_ACTION_PATTERNS):
            return "user_preference"
        if has_constraint and not self._looks_like_question(text):
            return "constraint"
        if has_task and has_task_action:
            return "action_item"
        if has_task_context or (has_task and len(text) >= 12):
            return "task_context"
        if has_summary and len(text) >= 12:
            return "session_summary"
        return None

    def _looks_like_question(self, text: str) -> bool:
        return self._matches_any(text, self._QUESTION_PATTERNS)

    @staticmethod
    def _normalize_candidate(text: str) -> str:
        compact = re.sub(r"\s+", " ", str(text or "")).strip()
        compact = re.sub(r"^[,.;:，。；：、\-\s]+", "", compact)
        compact = re.sub(
            r"^(我觉得|我想|我希望|那个|就是|嗯|呃|请帮我|帮我|麻烦你|简单说|结论是)\s*",
            "",
            compact,
            flags=re.IGNORECASE,
        )
        compact = compact.strip()
        if len(compact) < 6:
            return ""
        return compact[:160]

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts: list[str] = []
        for segment in re.split(r"[。！？!?\n;；]+", str(text or "")):
            if not segment.strip():
                continue
            clauses = [item.strip() for item in re.split(r"[，,]+", segment) if item.strip()]
            parts.extend(clauses or [segment.strip()])
        return parts

    @staticmethod
    def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    @classmethod
    def _prune_pending_entries(cls, scope: str) -> list[dict[str, Any]]:
        cls._load_pending_cache_from_disk()
        now = time.time()
        entries = cls._PENDING_MEMORY_CACHE.get(scope, [])
        fresh = [
            item for item in entries
            if now - float(item.get("created_at", 0.0)) <= cls._PENDING_MEMORY_TTL_SECONDS
        ]
        if fresh:
            cls._PENDING_MEMORY_CACHE[scope] = fresh[-cls._PENDING_MEMORY_MAX_PER_SCOPE :]
        else:
            cls._PENDING_MEMORY_CACHE.pop(scope, None)
        cls._save_pending_cache_to_disk()
        return cls._PENDING_MEMORY_CACHE.get(scope, [])

    @classmethod
    def _queue_pending_entries(cls, scope: str, entries: list[str]) -> int:
        if not scope or not entries:
            return 0
        existing = cls._prune_pending_entries(scope)
        seen = {cls._content_dedupe_key(str(item.get("content", ""))) for item in existing}
        now = time.time()
        appended = 0
        for entry in entries:
            key = cls._content_dedupe_key(entry)
            if not key or key in seen:
                continue
            existing.append({"content": entry, "created_at": now})
            seen.add(key)
            appended += 1
        cls._PENDING_MEMORY_CACHE[scope] = existing[-cls._PENDING_MEMORY_MAX_PER_SCOPE :]
        cls._save_pending_cache_to_disk()
        return appended

    @classmethod
    def _search_pending_entries(cls, scope: str, query: str) -> list[dict[str, Any]]:
        pending = cls._prune_pending_entries(scope)
        if not pending:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for item in pending:
            content = str(item.get("content", "")).strip()
            score = cls._score_pending_entry(query, content)
            if score < 0.18:
                continue
            scored.append((score, {"content": content, "source": "local_pending"}))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:3]]

    @classmethod
    def _merge_retrieved_memories(
        cls,
        *,
        local_memories: list[dict[str, Any]],
        cloud_memories: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()

        for memory in local_memories:
            content = str(memory.get("content", "")).strip()
            key = cls._content_dedupe_key(content)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append({"content": content, "source": "local_pending"})

        for memory in cloud_memories:
            content = str(memory.get("content", "")).strip()
            key = cls._content_dedupe_key(content)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append({"content": content, "source": "cloud"})

        return merged

    @classmethod
    def _load_pending_cache_from_disk(cls) -> None:
        path = cls._PENDING_CACHE_PATH
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError, TypeError):
            logger.warning("voice_memory_pending load_failed path=%s", path)
            return

        if not isinstance(raw, dict):
            return

        loaded: dict[str, list[dict[str, Any]]] = {}
        for scope, items in raw.items():
            if not isinstance(scope, str) or not isinstance(items, list):
                continue
            normalized_items: list[dict[str, Any]] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                content = str(item.get("content", "")).strip()
                if not content:
                    continue
                try:
                    created_at = float(item.get("created_at", 0.0))
                except (TypeError, ValueError):
                    created_at = 0.0
                normalized_items.append({"content": content, "created_at": created_at})
            if normalized_items:
                loaded[scope] = normalized_items[-cls._PENDING_MEMORY_MAX_PER_SCOPE :]
        cls._PENDING_MEMORY_CACHE = loaded

    @classmethod
    def _save_pending_cache_to_disk(cls) -> None:
        path = cls._PENDING_CACHE_PATH
        serializable: dict[str, list[dict[str, Any]]] = {}
        for scope, items in cls._PENDING_MEMORY_CACHE.items():
            normalized_items = [
                {
                    "content": str(item.get("content", "")).strip(),
                    "created_at": float(item.get("created_at", 0.0)),
                }
                for item in items
                if str(item.get("content", "")).strip()
            ]
            if normalized_items:
                serializable[scope] = normalized_items
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(serializable, ensure_ascii=True), encoding="utf-8")
            temp_path.replace(path)
        except OSError:
            logger.warning("voice_memory_pending save_failed path=%s", path)

    @classmethod
    def _score_pending_entry(cls, query: str, content: str) -> float:
        normalized_query = cls._search_text(query)
        normalized_content = cls._search_text(content)
        if not normalized_query or not normalized_content:
            return 0.0
        if normalized_query in normalized_content:
            return 1.0
        if normalized_content in normalized_query:
            return 0.9

        query_grams = cls._bigrams(normalized_query)
        content_grams = cls._bigrams(normalized_content)
        overlap = len(query_grams & content_grams) / max(1, len(query_grams))
        pattern_bonus = 0.0
        if cls._matches_any(query, cls._TASK_PATTERNS) and cls._matches_any(content, cls._TASK_PATTERNS):
            pattern_bonus += 0.2
        if cls._matches_any(query, cls._PREFERENCE_PATTERNS) and cls._matches_any(content, cls._PREFERENCE_PATTERNS):
            pattern_bonus += 0.2
        if cls._matches_any(query, cls._VOICE_PATTERNS) and cls._matches_any(content, cls._VOICE_PATTERNS):
            pattern_bonus += 0.2
        return overlap + pattern_bonus

    @staticmethod
    def _search_text(text: str) -> str:
        value = str(text or "").strip().lower()
        value = re.sub(r"^\[[^\]]+\]\s*", "", value)
        value = re.sub(r"^[^:：]{1,24}[:：]\s*", "", value)
        value = re.sub(r"\s+", "", value)
        value = re.sub(r"[^\w\u4e00-\u9fff]+", "", value)
        return value

    @classmethod
    def _content_dedupe_key(cls, text: str) -> str:
        return cls._search_text(text)

    @staticmethod
    def _bigrams(text: str) -> set[str]:
        if len(text) <= 2:
            return {text} if text else set()
        return {text[idx : idx + 2] for idx in range(len(text) - 1)}


class DashScopeRealtimeCallback:
    def __init__(self, *, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.loop = loop
        self.queue = queue

    def _push(self, event: dict[str, Any]) -> None:
        self.loop.call_soon_threadsafe(self.queue.put_nowait, event)

    def on_open(self) -> None:
        return None

    def on_event(self, response: Any) -> None:
        if not isinstance(response, dict):
            return

        event_type = str(response.get("type", "")).strip()
        if event_type == "input_audio_buffer.speech_started":
            self._push({"type": "interrupted"})
            return
        if event_type == "conversation.item.input_audio_transcription.completed":
            transcript = str(response.get("transcript", "")).strip()
            if transcript:
                self._push({"type": "user_transcript", "text": transcript})
            return
        if event_type == "response.audio.delta":
            delta = str(response.get("delta", "")).strip()
            if delta:
                self._push(
                    {
                        "type": "assistant_audio",
                        "audio": delta,
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000,
                    }
                )
            return
        if event_type in {"response.audio_transcript.delta", "response.text.delta"}:
            delta = str(response.get("delta", ""))
            if delta:
                self._push({"type": "assistant_text", "text": delta})
            return
        if event_type == "response.done":
            self._push({"type": "turn_complete"})
            return
        if event_type == "error":
            error_data = response.get("error")
            if isinstance(error_data, dict):
                message = str(error_data.get("message", "")).strip() or str(response)
            else:
                message = str(error_data or response).strip()
            self._push({"type": "error", "message": message})

    def on_close(self, close_status_code: Any, close_msg: Any) -> None:
        self._push(
            {
                "type": "closed",
                "code": int(close_status_code or 1000),
                "message": str(close_msg or "").strip(),
            }
        )


class RealtimeVoiceService:
    def __init__(self, config: BackendConfig | None = None):
        self.config = config or BackendConfig()

    @staticmethod
    def _build_realtime_instructions(memory_context: str = "") -> str:
        if not memory_context:
            return BASE_REALTIME_INSTRUCTIONS
        return (
            f"{BASE_REALTIME_INSTRUCTIONS}\n\n"
            "Relevant long-term memories for personalization. Use them only when they genuinely help. "
            "Do not quote or mention this memory block unless the user directly asks.\n"
            f"{memory_context}"
        )

    @staticmethod
    def _build_recall_miss_instructions(user_query: str) -> str:
        return (
            f"{BASE_REALTIME_INSTRUCTIONS}\n\n"
            "The user is explicitly asking you to recall prior conversation memory, but no matching long-term "
            "memory was retrieved for this turn. Do not pretend you remember specific prior facts. "
            "State briefly that you could not retrieve a matching saved memory, then ask the user to restate "
            "the detail if needed.\n"
            f"Current user query: {user_query}"
        )

    @staticmethod
    def _build_google_memory_prefill_turns(memory_context: str) -> list[dict[str, Any]]:
        if not memory_context.strip():
            return []
        return [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Context note for personalization only. These long-term memories may help with "
                            "the user's next turn. Use them only when relevant, and do not mention this note.\n"
                            f"{memory_context}"
                        )
                    }
                ],
            }
        ]

    async def _apply_google_memory_prefill(self, session: Any, memory_context: str) -> None:
        turns = self._build_google_memory_prefill_turns(memory_context)
        if not turns:
            return
        try:
            await session.send_client_content(turns=turns, turn_complete=False)
        except Exception:
            return

    def _resolve_google_settings(self, model: str | None) -> dict[str, str]:
        provider_settings = self.config.get_provider_settings("Google", model)
        resolved_model = provider_settings["model"].strip() or DEFAULT_GOOGLE_REALTIME_MODEL
        api_key = provider_settings["api_key"].strip()
        base_url = provider_settings["base_url"].strip()
        if not api_key:
            raise RuntimeError("Google API Key 未配置，无法启动实时语音会话。")
        if genai is None or types is None:
            raise RuntimeError("google-genai 依赖未安装，无法启动实时语音会话。")
        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": resolved_model,
        }

    def _resolve_dashscope_settings(self, model: str | None) -> dict[str, str]:
        provider_settings = self.config.get_provider_settings("DashScope", model)
        resolved_model = provider_settings["model"].strip() or DEFAULT_DASHSCOPE_REALTIME_MODEL
        api_key = provider_settings["api_key"].strip()
        base_url = provider_settings["base_url"].strip().lower()
        if not api_key:
            raise RuntimeError("DashScope API Key 未配置，无法启动实时语音会话。")
        if OmniRealtimeConversation is None or MultiModality is None or AudioFormat is None:
            raise RuntimeError("DashScope Omni Realtime 依赖未安装，无法启动实时语音会话。")
        region = "intl" if "dashscope-intl" in base_url else "cn"
        return {
            "api_key": api_key,
            "model": resolved_model,
            "region": region,
        }

    @staticmethod
    async def _send_event(websocket: WebSocket, event_type: str, **payload: Any) -> None:
        await websocket.send_json({"type": event_type, **payload})

    @staticmethod
    def _extract_transcript_text(server_content: Any, candidate_names: tuple[str, ...]) -> str:
        for attr_name in candidate_names:
            if not hasattr(server_content, attr_name):
                continue
            value = getattr(server_content, attr_name)
            if not value:
                continue
            if hasattr(value, "text") and getattr(value, "text", ""):
                return str(value.text).strip()
            return str(value).strip()
        return ""

    @staticmethod
    def _build_live_config(voice: str):
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=BASE_REALTIME_INSTRUCTIONS,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    prefix_padding_ms=500,
                    silence_duration_ms=800,
                )
            ),
        )

    async def _client_to_google_loop(
        self,
        websocket: WebSocket,
        session: Any,
        memory_session: RealtimeMemorySession,
    ) -> None:
        while True:
            message = await websocket.receive()
            message_type = message.get("type")
            if message_type == "websocket.disconnect":
                break

            text_data = message.get("text")
            if text_data:
                try:
                    payload = json.loads(text_data)
                except Exception:
                    await self._send_event(websocket, "error", message="无效的实时语音消息。")
                    continue
                command_type = str(payload.get("type", "")).strip()
                if command_type == "config":
                    memory_session.configure(payload.get("memory"))
                    await self._send_event(
                        websocket,
                        "memory_config",
                        enabled=bool(memory_session._config.get_service()),
                        scope=memory_session._config.memory_scope,
                    )
                    continue
                if command_type == "text_input":
                    content = str(payload.get("text", "")).strip()
                    if content:
                        await session.send(input=content, end_of_turn=True)
                    continue
                if command_type == "ping":
                    await self._send_event(websocket, "pong")
                    continue
                if command_type == "stop":
                    break
                continue

            audio_bytes = message.get("bytes")
            if audio_bytes:
                await session.send_realtime_input(
                    audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                )

    async def _google_to_client_loop(
        self,
        websocket: WebSocket,
        session: Any,
        memory_session: RealtimeMemorySession,
    ) -> None:
        pending_prefill_context = ""
        while True:
            turn = session.receive()
            async for response in turn:
                audio_data = getattr(response, "data", None)
                if audio_data:
                    await self._send_event(
                        websocket,
                        "assistant_audio",
                        audio=base64.b64encode(audio_data).decode("ascii"),
                        encoding="pcm_s16le",
                        sample_rate=24000,
                    )

                response_text = getattr(response, "text", None)
                if response_text:
                    memory_session.note_assistant_text(str(response_text))
                    await self._send_event(websocket, "assistant_text", text=str(response_text))

                server_content = getattr(response, "server_content", None)
                if not server_content:
                    continue

                if getattr(server_content, "interrupted", False):
                    await self._send_event(websocket, "interrupted")

                user_text = self._extract_transcript_text(
                    server_content,
                    ("input_transcription", "input_audio_transcription", "transcription"),
                )
                if user_text:
                    memory_session.note_user_transcript(user_text)
                    retrieval = await memory_session.retrieve_memory_context()
                    memory_context = str(retrieval.get("context", ""))
                    memory_count = int(retrieval.get("memories_retrieved", 0))
                    local_pending_count = int(retrieval.get("local_pending_count", 0))
                    cloud_count = int(retrieval.get("cloud_count", 0))
                    if retrieval.get("attempted"):
                        await self._send_event(
                            websocket,
                            "memory_context",
                            memories_retrieved=memory_count,
                            local_pending_count=local_pending_count,
                            cloud_count=cloud_count,
                            attempted=True,
                        )
                    if memory_context:
                        logger.info(
                            "voice_memory_inject provider=Google scope=%s count=%s local_pending=%s cloud=%s",
                            memory_session._config.memory_scope,
                            memory_count,
                            local_pending_count,
                            cloud_count,
                        )
                        pending_prefill_context = memory_context
                    await self._send_event(websocket, "user_transcript", text=user_text)

                assistant_transcript = self._extract_transcript_text(
                    server_content,
                    ("output_transcription", "output_audio_transcription"),
                )
                if assistant_transcript:
                    memory_session.note_assistant_text(assistant_transcript)
                    await self._send_event(websocket, "assistant_text", text=assistant_transcript)

                if getattr(server_content, "turn_complete", False):
                    memory_result = await memory_session.flush_turn()
                    await self._send_event(
                        websocket,
                        "memory_write",
                        attempted_count=int(memory_result.get("attempted_count", 0)),
                        saved_count=int(memory_result.get("saved_count", 0)),
                        failed_count=int(memory_result.get("failed_count", 0)),
                        local_pending_count=int(memory_result.get("local_pending_count", 0)),
                        reason=str(memory_result.get("reason", "")),
                    )
                    if pending_prefill_context:
                        await self._apply_google_memory_prefill(session, pending_prefill_context)
                        pending_prefill_context = ""
                    await self._send_event(websocket, "turn_complete")

    async def _client_to_dashscope_loop(
        self,
        websocket: WebSocket,
        conversation: Any,
        memory_session: RealtimeMemorySession,
    ) -> None:
        while True:
            message = await websocket.receive()
            message_type = message.get("type")
            if message_type == "websocket.disconnect":
                break

            text_data = message.get("text")
            if text_data:
                try:
                    payload = json.loads(text_data)
                except Exception:
                    await self._send_event(websocket, "error", message="无效的实时语音消息。")
                    continue
                command_type = str(payload.get("type", "")).strip()
                if command_type == "config":
                    memory_session.configure(payload.get("memory"))
                    await self._send_event(
                        websocket,
                        "memory_config",
                        enabled=bool(memory_session._config.get_service()),
                        scope=memory_session._config.memory_scope,
                    )
                    continue
                if command_type == "ping":
                    await self._send_event(websocket, "pong")
                    continue
                if command_type == "stop":
                    break
                continue

            audio_bytes = message.get("bytes")
            if audio_bytes:
                conversation.append_audio(base64.b64encode(audio_bytes).decode("ascii"))

    async def _dashscope_to_client_loop(
        self,
        websocket: WebSocket,
        queue: asyncio.Queue[dict[str, Any]],
        memory_session: RealtimeMemorySession,
        conversation: Any,
        voice: str,
    ) -> None:
        while True:
            event = await queue.get()
            event_type = str(event.get("type", "")).strip()
            if event_type == "closed":
                break
            if event_type == "user_transcript":
                user_text = str(event.get("text", ""))
                memory_session.note_user_transcript(user_text)
                retrieval = await memory_session.retrieve_memory_context()
                memory_context = str(retrieval.get("context", ""))
                memory_count = int(retrieval.get("memories_retrieved", 0))
                local_pending_count = int(retrieval.get("local_pending_count", 0))
                cloud_count = int(retrieval.get("cloud_count", 0))
                if retrieval.get("attempted"):
                    await self._send_event(
                        websocket,
                        "memory_context",
                        memories_retrieved=memory_count,
                        local_pending_count=local_pending_count,
                        cloud_count=cloud_count,
                        attempted=True,
                    )
                if memory_context:
                    logger.info(
                        "voice_memory_inject provider=DashScope scope=%s count=%s local_pending=%s cloud=%s",
                        memory_session._config.memory_scope,
                        memory_count,
                        local_pending_count,
                        cloud_count,
                    )
                    conversation.update_session(
                        output_modalities=[MultiModality.AUDIO, MultiModality.TEXT],  # type: ignore[union-attr]
                        voice=voice,
                        input_audio_format=AudioFormat.PCM_16000HZ_MONO_16BIT,  # type: ignore[union-attr]
                        output_audio_format=AudioFormat.PCM_24000HZ_MONO_16BIT,  # type: ignore[union-attr]
                        enable_input_audio_transcription=True,
                        enable_turn_detection=True,
                        instructions=self._build_realtime_instructions(memory_context),
                    )
                elif memory_session.is_forced_recall_query(user_text):
                    logger.info(
                        "voice_memory_inject provider=DashScope scope=%s count=0 forced_recall=true",
                        memory_session._config.memory_scope,
                    )
                    conversation.update_session(
                        output_modalities=[MultiModality.AUDIO, MultiModality.TEXT],  # type: ignore[union-attr]
                        voice=voice,
                        input_audio_format=AudioFormat.PCM_16000HZ_MONO_16BIT,  # type: ignore[union-attr]
                        output_audio_format=AudioFormat.PCM_24000HZ_MONO_16BIT,  # type: ignore[union-attr]
                        enable_input_audio_transcription=True,
                        enable_turn_detection=True,
                        instructions=self._build_recall_miss_instructions(user_text),
                    )
            elif event_type == "assistant_text":
                memory_session.note_assistant_text(str(event.get("text", "")))
            elif event_type == "turn_complete":
                memory_result = await memory_session.flush_turn()
                await self._send_event(
                    websocket,
                    "memory_write",
                    attempted_count=int(memory_result.get("attempted_count", 0)),
                    saved_count=int(memory_result.get("saved_count", 0)),
                    failed_count=int(memory_result.get("failed_count", 0)),
                    local_pending_count=int(memory_result.get("local_pending_count", 0)),
                    reason=str(memory_result.get("reason", "")),
                )
                conversation.update_session(
                    output_modalities=[MultiModality.AUDIO, MultiModality.TEXT],  # type: ignore[union-attr]
                    voice=voice,
                    input_audio_format=AudioFormat.PCM_16000HZ_MONO_16BIT,  # type: ignore[union-attr]
                    output_audio_format=AudioFormat.PCM_24000HZ_MONO_16BIT,  # type: ignore[union-attr]
                    enable_input_audio_transcription=True,
                    enable_turn_detection=True,
                    instructions=self._build_realtime_instructions(),
                )
            await websocket.send_json(event)
            if event_type == "error":
                break

    async def stream_google_session(
        self,
        websocket: WebSocket,
        *,
        model: str | None = None,
        voice: str = DEFAULT_GOOGLE_REALTIME_VOICE,
    ) -> None:
        settings = self._resolve_google_settings(model)
        memory_session = RealtimeMemorySession()
        http_options: dict[str, str] = {"api_version": "v1beta"}
        if settings["base_url"]:
            http_options["base_url"] = settings["base_url"]

        client = genai.Client(api_key=settings["api_key"], http_options=http_options)
        live_config = self._build_live_config(voice)

        try:
            async with client.aio.live.connect(model=settings["model"], config=live_config) as session:
                await self._send_event(
                    websocket,
                    "session_open",
                    provider="Google",
                    model=settings["model"],
                    voice=voice,
                )
                send_task = asyncio.create_task(
                    self._client_to_google_loop(websocket, session, memory_session)
                )
                receive_task = asyncio.create_task(
                    self._google_to_client_loop(websocket, session, memory_session)
                )
                done, pending = await asyncio.wait(
                    {send_task, receive_task},
                    return_when=asyncio.FIRST_EXCEPTION,
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    task.result()
        except WebSocketDisconnect:
            return
        except Exception as e:
            print(f"DEBUG: Google Realtime Session Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await self._send_event(websocket, "error", message=f"Google 实时会话启动失败: {str(e)}")
            return
        finally:
            memory_session.flush_turn()
            await memory_session.drain()

    async def stream_dashscope_session(
        self,
        websocket: WebSocket,
        *,
        model: str | None = None,
        voice: str = DEFAULT_DASHSCOPE_REALTIME_VOICE,
    ) -> None:
        settings = self._resolve_dashscope_settings(model)
        memory_session = RealtimeMemorySession()
        import dashscope

        dashscope.api_key = settings["api_key"]
        base_domain = "dashscope.aliyuncs.com" if settings["region"] == "cn" else "dashscope-intl.aliyuncs.com"
        url = f"wss://{base_domain}/api-ws/v1/realtime"
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        callback = DashScopeRealtimeCallback(loop=loop, queue=event_queue)
        conversation = OmniRealtimeConversation(  # type: ignore[misc]
            model=settings["model"],
            callback=callback,
            url=url,
        )

        try:
            conversation.connect()
            await asyncio.sleep(0.5)
            conversation.update_session(
                output_modalities=[MultiModality.AUDIO, MultiModality.TEXT],  # type: ignore[union-attr]
                voice=voice,
                input_audio_format=AudioFormat.PCM_16000HZ_MONO_16BIT,  # type: ignore[union-attr]
                output_audio_format=AudioFormat.PCM_24000HZ_MONO_16BIT,  # type: ignore[union-attr]
                enable_input_audio_transcription=True,
                enable_turn_detection=True,
                instructions=self._build_realtime_instructions(),
            )
            await asyncio.sleep(0.5)
            await self._send_event(
                websocket,
                "session_open",
                provider="DashScope",
                model=settings["model"],
                voice=voice,
            )

            send_task = asyncio.create_task(
                self._client_to_dashscope_loop(websocket, conversation, memory_session)
            )
            receive_task = asyncio.create_task(
                self._dashscope_to_client_loop(
                    websocket,
                    event_queue,
                    memory_session,
                    conversation,
                    voice,
                )
            )
            done, pending = await asyncio.wait(
                {send_task, receive_task},
                return_when=asyncio.FIRST_EXCEPTION,
            )
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
        except WebSocketDisconnect:
            return
        except Exception as e:
            print(f"DEBUG: DashScope Realtime Session Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await self._send_event(websocket, "error", message=f"DashScope 实时会话启动失败: {str(e)}")
            return
        finally:
            memory_session.flush_turn()
            await memory_session.drain()
            try:
                conversation.close()
            except Exception:
                pass

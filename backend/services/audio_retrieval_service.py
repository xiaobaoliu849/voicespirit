from __future__ import annotations

from typing import Any

from .audio_research_service import AudioResearchService
from .evermem_config import EverMemConfig


class AudioRetrievalService:
    def __init__(
        self,
        research_service: AudioResearchService | None = None,
        *,
        max_sources: int = 8,
    ) -> None:
        self.research_service = research_service or AudioResearchService()
        self.max_sources = max(1, min(int(max_sources), 20))

    @staticmethod
    def _clean_text(value: str | None, *, limit: int) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        return text[:limit]

    @staticmethod
    def _normalize_source(source: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_type": str(source.get("source_type", "manual_text")),
            "title": str(source.get("title", ""))[:240],
            "uri": str(source.get("uri", ""))[:1000],
            "snippet": str(source.get("snippet", ""))[:500],
            "content": str(source.get("content", ""))[:5000],
            "score": float(source.get("score", 0.0) or 0.0),
            "meta": dict(source.get("meta", {})) if isinstance(source.get("meta"), dict) else {},
        }

    @staticmethod
    def _source_key(source: dict[str, Any]) -> str:
        uri = str(source.get("uri", "")).strip().lower()
        if uri:
            return f"uri:{uri}"
        body = str(source.get("content") or source.get("snippet") or "").strip().lower()
        return f"text:{body[:240]}"

    def _append_source(
        self,
        sources: list[dict[str, Any]],
        seen: set[str],
        source: dict[str, Any],
    ) -> bool:
        if len(sources) >= self.max_sources:
            return False
        normalized = self._normalize_source(source)
        key = self._source_key(normalized)
        if not key or key in seen:
            return False
        if not (
            normalized.get("uri")
            or normalized.get("content")
            or normalized.get("snippet")
        ):
            return False
        seen.add(key)
        sources.append(normalized)
        return True

    async def _fetch_url_source(
        self,
        url: str,
        *,
        title_hint: str = "",
        snippet_hint: str = "",
        source_type: str,
        score: float,
    ) -> dict[str, Any] | None:
        clean_url = str(url or "").strip()
        if not clean_url:
            return None
        try:
            document = await self.research_service.fetch_document(
                clean_url,
                title_hint=title_hint,
                snippet_hint=snippet_hint,
                source_type=source_type,
                score=score,
            )
        except Exception:
            return None
        source = document.to_source()
        return {
            "source_type": str(source.get("source_type", source_type)),
            "title": str(source.get("title", "")),
            "uri": str(source.get("uri", source.get("url", clean_url))),
            "snippet": str(source.get("snippet", "")),
            "content": str(source.get("content", "")),
            "score": float(source.get("score", score) or 0.0),
            "meta": dict(source.get("meta", {})) if isinstance(source.get("meta"), dict) else {},
        }

    async def _collect_web_search_sources(
        self,
        *,
        topic: str,
        remaining_slots: int,
    ) -> list[dict[str, Any]]:
        if remaining_slots <= 0:
            return []
        try:
            results = await self.research_service.search(topic, limit=remaining_slots)
        except Exception:
            return []

        sources: list[dict[str, Any]] = []
        for item in results:
            source = await self._fetch_url_source(
                str(item.get("url", "")),
                title_hint=str(item.get("title", "")),
                snippet_hint=str(item.get("snippet", "")),
                source_type="web_search",
                score=0.7,
            )
            if source is not None:
                sources.append(source)
        return sources

    async def collect_sources(
        self,
        *,
        topic: str,
        use_memory: bool,
        source_urls: list[str] | None = None,
        source_text: str | None = None,
        request_headers: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()

        clean_source_text = self._clean_text(source_text, limit=4000)
        if clean_source_text:
            self._append_source(
                sources,
                seen,
                {
                    "source_type": "manual_text",
                    "title": "User provided context",
                    "uri": "",
                    "snippet": clean_source_text[:280],
                    "content": clean_source_text,
                    "score": 1.0,
                    "meta": {"origin": "user_input"},
                }
            )

        for idx, item in enumerate(source_urls or [], start=1):
            clean_url = str(item or "").strip()
            if not clean_url:
                continue
            source = await self._fetch_url_source(
                clean_url,
                title_hint=f"Manual source {idx}",
                snippet_hint=clean_url[:280],
                source_type="manual_url",
                score=0.8,
            )
            if source is None:
                source = {
                    "source_type": "manual_url",
                    "title": f"Manual source {idx}",
                    "uri": clean_url[:1000],
                    "snippet": clean_url[:280],
                    "content": "",
                    "score": 0.5,
                    "meta": {"origin": "user_url", "fetch_status": "unavailable"},
                }
            self._append_source(sources, seen, source)
            if len(sources) >= self.max_sources:
                break

        if use_memory:
            evermem_config = EverMemConfig()
            if request_headers:
                evermem_config.update_from_headers(request_headers)
            evermem_service = evermem_config.get_service()
            if evermem_service and not evermem_service.should_skip_memory(topic):
                memories = await evermem_service.search_memories(
                    query=topic,
                    user_id=evermem_config.memory_scope,
                    min_score=0.3,
                )
                for idx, memory in enumerate(memories[:5], start=1):
                    if len(sources) >= self.max_sources:
                        break
                    content = self._clean_text(str(memory.get("content", "")), limit=1200)
                    if not content:
                        continue
                    self._append_source(
                        sources,
                        seen,
                        {
                            "source_type": "evermem",
                            "title": f"Memory {idx}",
                            "uri": "",
                            "snippet": content[:280],
                            "content": content,
                            "score": float(memory.get("score", 0.0) or 0.0),
                            "meta": {
                                "memory_type": str(memory.get("type", "")),
                                "origin": "evermem",
                            },
                        }
                    )

        if not clean_source_text and len(sources) < 2:
            search_sources = await self._collect_web_search_sources(
                topic=topic,
                remaining_slots=self.max_sources - len(sources),
            )
            for source in search_sources:
                self._append_source(sources, seen, source)
        return sources

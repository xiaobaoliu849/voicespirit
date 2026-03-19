from __future__ import annotations

from typing import Any

from .evermem_config import EverMemConfig


class AudioRetrievalService:
    @staticmethod
    def _clean_text(value: str | None, *, limit: int) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        return text[:limit]

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

        clean_source_text = self._clean_text(source_text, limit=4000)
        if clean_source_text:
            sources.append(
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
            sources.append(
                {
                    "source_type": "manual_url",
                    "title": f"Manual source {idx}",
                    "uri": clean_url[:1000],
                    "snippet": clean_url[:280],
                    "content": "",
                    "score": 0.5,
                    "meta": {"origin": "user_url"},
                }
            )

        if not use_memory:
            return sources

        evermem_config = EverMemConfig()
        if request_headers:
            evermem_config.update_from_headers(request_headers)
        evermem_service = evermem_config.get_service()
        if not evermem_service:
            return sources
        if evermem_service.should_skip_memory(topic):
            return sources

        memories = await evermem_service.search_memories(
            query=topic,
            user_id=evermem_config.memory_scope,
            min_score=0.3,
        )
        for idx, memory in enumerate(memories[:5], start=1):
            content = self._clean_text(str(memory.get("content", "")), limit=1200)
            if not content:
                continue
            sources.append(
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
        return sources

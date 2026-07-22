from __future__ import annotations

from typing import Any

from .llm_service import LLMService
from .script_parser import parse_script_with_fallback, normalize_script_lines


class AudioScriptWriter:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    @staticmethod
    def _normalize_language(value: str | None) -> str:
        text = str(value or "").strip().lower()
        if text.startswith("en"):
            return "en"
        return "zh"

    @staticmethod
    def _build_evidence_summary(sources: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for idx, source in enumerate(sources[:6], start=1):
            title = str(source.get("title", "")).strip()
            uri = str(source.get("uri", "")).strip()
            snippet = str(source.get("snippet", "")).strip()
            content = str(source.get("content", "")).strip()
            body = snippet or content
            if not body:
                body = f"参考来源：{uri}" if uri else ""
            if not body:
                continue
            prefix = f"{idx}. {title}: " if title else f"{idx}. "
            citation = f" [{uri}]" if uri else ""
            lines.append(f"{prefix}{body[:480]}{citation}")
        return "\n".join(lines)

    @staticmethod
    def _build_research_brief(sources: list[dict[str, Any]]) -> str:
        source_counts: dict[str, int] = {}
        lines: list[str] = []
        for source in sources:
            source_type = str(source.get("source_type", "unknown")).strip() or "unknown"
            source_counts[source_type] = source_counts.get(source_type, 0) + 1

        if source_counts:
            mix = ", ".join(
                f"{source_type}={count}"
                for source_type, count in sorted(source_counts.items())
            )
            lines.append(f"Source mix: {mix}")
        else:
            lines.append("Source mix: none")

        for idx, source in enumerate(sources[:8], start=1):
            title = str(source.get("title", "")).strip() or f"Source {idx}"
            source_type = str(source.get("source_type", "")).strip() or "unknown"
            uri = str(source.get("uri", "")).strip()
            score = float(source.get("score", 0.0) or 0.0)
            snippet = str(source.get("snippet") or source.get("content") or "").strip()[:240]
            uri_part = f" {uri}" if uri else ""
            snippet_part = f" - {snippet}" if snippet else ""
            lines.append(f"{idx}. {title} ({source_type}, score={score:.2f}):{uri_part}{snippet_part}")
        return "\n".join(lines)

    @staticmethod
    def _build_system_prompt(language: str, has_evidence: bool) -> str:
        if language == "en":
            base = (
                "You are an audio script writer for a two-speaker podcast. "
                "Return only dialogue lines in the format 'A: ...' and 'B: ...'. "
                "Write naturally for spoken audio."
            )
            if has_evidence:
                return (
                    base
                    + " Use the supplied evidence when it helps. Do not invent unsupported specifics."
                )
            return base + " Keep claims general and avoid unsupported specifics."

        base = (
            "你是一个双人播客脚本写手。"
            "只输出对话台词，每行严格使用 'A: ...' 或 'B: ...' 的格式。"
            "语气自然、适合口播。"
        )
        if has_evidence:
            return base + " 优先利用提供的资料，不要编造没有依据的细节。"
        return base + " 在资料不足时保持概括表达，不要编造事实。"

    @staticmethod
    def _build_user_prompt(
        *,
        topic: str,
        language: str,
        turn_count: int,
        evidence_summary: str,
        generation_constraints: str,
    ) -> str:
        if language == "en":
            prompt = (
                f"Topic: {topic}\n\n"
                f"Please write a two-speaker podcast dialogue with {turn_count} rounds.\n"
                "A is the host and B is the guest expert.\n"
                "Include a natural opening and closing.\n"
                "Each line should be concise and easy to read aloud.\n"
            )
            if evidence_summary:
                prompt += f"\nEvidence:\n{evidence_summary}\n"
            if generation_constraints:
                prompt += f"\nAdditional constraints:\n{generation_constraints[:1800]}\n"
            return prompt

        prompt = (
            f"主题：{topic}\n\n"
            f"请写一段双人播客对话，共 {turn_count} 轮。\n"
            "A 是主持人，B 是嘉宾专家。\n"
            "包含自然开场和收尾。\n"
            "每句适合口播，不要太书面化。\n"
        )
        if evidence_summary:
            prompt += f"\n可参考资料：\n{evidence_summary}\n"
        if generation_constraints:
            prompt += f"\n额外约束：\n{generation_constraints[:1800]}\n"
        return prompt

    async def generate_script(
        self,
        *,
        topic: str,
        language: str,
        turn_count: int,
        provider: str,
        model: str | None,
        sources: list[dict[str, Any]],
        generation_constraints: str = "",
    ) -> dict[str, Any]:
        clean_language = self._normalize_language(language)
        evidence_summary = self._build_evidence_summary(sources)
        research_brief = self._build_research_brief(sources)
        prompt_evidence = "\n\n".join(
            item for item in (research_brief, evidence_summary) if item
        )
        completion = await self.llm_service.chat_completion(
            provider=provider,
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": self._build_system_prompt(
                        clean_language,
                        has_evidence=bool(evidence_summary),
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_user_prompt(
                        topic=topic,
                        language=clean_language,
                        turn_count=max(2, min(int(turn_count), 40)),
                        evidence_summary=prompt_evidence,
                        generation_constraints=str(generation_constraints or "").strip(),
                    ),
                },
            ],
            temperature=0.7,
            max_tokens=max(1200, max(2, min(int(turn_count), 40)) * 220),
        )
        reply = str(completion.get("reply", "")).strip()
        parsed = parse_script_with_fallback(reply)
        normalized = normalize_script_lines(parsed)
        if len(normalized) < 2:
            raise RuntimeError("Generated script is too short or cannot be parsed.")
        return {
            "provider": str(completion.get("provider", provider)),
            "model": str(completion.get("model", model or "")),
            "reply": reply,
            "script_lines": normalized,
            "evidence_summary": evidence_summary,
            "research_brief": research_brief,
        }

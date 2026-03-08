from __future__ import annotations

import json
from typing import Any, AsyncGenerator
import base64

import httpx

from .config_loader import BackendConfig
from .evermem_config import EverMemConfig

SUPPORTED_PROVIDERS = {"DeepSeek", "OpenRouter", "SiliconFlow", "Groq", "DashScope"}


class LLMService:
    def __init__(self, config: BackendConfig | None = None):
        self.config = config or BackendConfig()

    @staticmethod
    def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in messages:
            role = str(item.get("role", "")).strip()
            content = item.get("content", "")
            if not role:
                continue
            if isinstance(content, str):
                cleaned = content.strip()
                if not cleaned:
                    continue
                normalized.append({"role": role, "content": cleaned})
                continue
            if isinstance(content, list):
                parts = [part for part in content if isinstance(part, dict)]
                if not parts:
                    continue
                normalized.append({"role": role, "content": parts})
        if not normalized:
            raise ValueError("messages is empty.")
        return normalized

    @staticmethod
    def _extract_reply(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text_parts.append(part["text"])
            return "\n".join(text_parts).strip()
        return ""

    @staticmethod
    def _extract_delta(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""

        delta = first.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts: list[str] = []
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        text_parts.append(part["text"])
                return "".join(text_parts)

        message = first.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        text_parts.append(part["text"])
                return "".join(text_parts)
        return ""

    def _resolve_settings(self, provider: str, model: str | None) -> dict[str, str]:
        self.config.reload()
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        settings = self.config.get_provider_settings(provider, model=model)
        if not settings["api_key"]:
            raise ValueError(f"Missing API key for provider: {provider}")
        if not settings["base_url"]:
            raise ValueError(f"Missing base URL for provider: {provider}")
        if not settings["model"]:
            raise ValueError(f"Missing model for provider: {provider}")
        return settings

    @staticmethod
    def _build_headers(provider: str, api_key: str) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider == "OpenRouter":
            headers["HTTP-Referer"] = "https://voicespirit.local"
            headers["X-Title"] = "VoiceSpirit"
        return headers

    async def chat_completion(
        self,
        *,
        provider: str,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        settings = self._resolve_settings(provider, model)

        normalized_messages = self._normalize_messages(messages)
        url = f"{settings['base_url']}/chat/completions"
        payload = {
            "model": settings["model"],
            "messages": normalized_messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "stream": False,
        }

        headers = self._build_headers(provider, settings["api_key"])

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            raise RuntimeError(f"Provider request failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Network error: {exc}") from exc

        data = response.json()
        reply = self._extract_reply(data)
        if not reply:
            raise RuntimeError("Provider returned empty response.")
        return {
            "provider": provider,
            "model": settings["model"],
            "reply": reply,
            "raw": data,
        }

    async def chat_completion_stream(
        self,
        *,
        provider: str,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        request_headers: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        settings = self._resolve_settings(provider, model)
        normalized_messages = self._normalize_messages(messages)
        
        # EverMemOS integration
        evermem_config = EverMemConfig()
        if request_headers:
            evermem_config.update_from_headers(request_headers)
        
        evermem_service = evermem_config.get_service()
        memory_scope = evermem_config.memory_scope
        memories_retrieved = 0
        memory_saved = False
        last_user_msg = None
        
        import asyncio
        if evermem_service:
            # Extract last user message
            last_user_msg = next(
                (m["content"] for m in reversed(normalized_messages) if m["role"] == "user"), 
                None
            )
            if isinstance(last_user_msg, list):
                # Simple extraction for multimodal
                text_parts = [p.get("text", "") for p in last_user_msg if isinstance(p, dict) and p.get("type") == "text"]
                last_user_msg = " ".join(text_parts).strip()
                
            if last_user_msg:
                # 1. Store user message (fire-and-forget)
                asyncio.create_task(
                    evermem_service.add_memory(
                        content=last_user_msg,
                        user_id=memory_scope,
                        sender=memory_scope,
                        sender_name="User"
                    )
                )
                memory_saved = True
                
                # 2. Retrieve memories
                if not evermem_service.should_skip_memory(last_user_msg):
                    try:
                        memories = await evermem_service.search_memories(
                            query=last_user_msg,
                            user_id=memory_scope,
                            min_score=0.3
                        )
                        if memories:
                            memories_retrieved = len(memories)
                            memory_context = "\n".join([m.get("content", "") for m in memories])
                            
                            # Inject into system prompt
                            sys_msg = next((m for m in normalized_messages if m["role"] == "system"), None)
                            memory_injection = f"\n\n【相关记忆】\n{memory_context}"
                            
                            if sys_msg:
                                if isinstance(sys_msg["content"], str):
                                    sys_msg["content"] += memory_injection
                            else:
                                normalized_messages.insert(0, {"role": "system", "content": f"系统提示：请利用以下用户记忆完成对话。{memory_injection}"})
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Failed to retrieve memories: {e}")

        url = f"{settings['base_url']}/chat/completions"
        payload = {
            "model": settings["model"],
            "messages": normalized_messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "stream": True,
        }
        headers = self._build_headers(provider, settings["api_key"])

        yield {"type": "meta", "provider": provider, "model": settings["model"]}
        chunks: list[str] = []
        try:
            timeout = httpx.Timeout(timeout=120.0, read=120.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip()
                        if not line or line.startswith(":"):
                            continue

                        data_line = line[5:].strip() if line.startswith("data:") else line
                        if not data_line:
                            continue
                        if data_line == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_line)
                        except json.JSONDecodeError:
                            continue

                        delta = self._extract_delta(chunk)
                        if delta:
                            chunks.append(delta)
                            yield {"type": "delta", "content": delta}
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            raise RuntimeError(f"Provider stream request failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Stream network error: {exc}") from exc

        reply = "".join(chunks).strip()
        if not reply:
            raise RuntimeError("Provider returned empty stream response.")
            
        # 3. Store assistant message (fire-and-forget)
        if evermem_service and reply:
            asyncio.create_task(
                evermem_service.add_memory(
                    content=reply,
                    user_id=memory_scope,
                    sender=f"{memory_scope}_assistant",
                    sender_name="Assistant"
                )
            )
            
        yield {
            "type": "done",
            "provider": provider,
            "model": settings["model"],
            "reply": reply,
            "memories_retrieved": memories_retrieved,
            "memory_saved": memory_saved,
        }

    async def translate_text(
        self,
        *,
        text: str,
        target_language: str,
        source_language: str | None = None,
        provider: str = "DashScope",
        model: str | None = None,
    ) -> dict[str, Any]:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("text is empty.")

        source = (source_language or "auto").strip()
        target = target_language.strip()
        if not target:
            raise ValueError("target_language is required.")

        system_prompt = (
            "You are a professional translator. "
            "Translate accurately and naturally. "
            "Return only the translated text, without explanation."
        )
        user_prompt = (
            f"Source language: {source}\n"
            f"Target language: {target}\n"
            f"Text:\n{cleaned}"
        )
        result = await self.chat_completion(
            provider=provider,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return {
            "provider": result["provider"],
            "model": result["model"],
            "translated_text": result["reply"],
        }

    async def translate_image(
        self,
        *,
        image_bytes: bytes,
        image_mime_type: str,
        target_language: str,
        source_language: str | None = None,
        provider: str = "DashScope",
        model: str | None = None,
    ) -> dict[str, Any]:
        if not image_bytes:
            raise ValueError("image_file is empty.")
        if not image_mime_type.startswith("image/"):
            raise ValueError("image_file must be an image.")

        source = (source_language or "auto").strip()
        target = target_language.strip()
        if not target:
            raise ValueError("target_language is required.")

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        system_prompt = (
            "You are a professional translator with OCR ability. "
            "Read the text from the image and translate it accurately and naturally. "
            "Return only the translated text, without explanation."
        )
        user_content = [
            {
                "type": "text",
                "text": (
                    f"Source language: {source}\n"
                    f"Target language: {target}\n"
                    "Task: extract and translate all readable text in the image."
                ),
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_mime_type};base64,{image_b64}"},
            },
        ]
        result = await self.chat_completion(
            provider=provider,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return {
            "provider": result["provider"],
            "model": result["model"],
            "translated_text": result["reply"],
        }

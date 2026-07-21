"""Shared EverMem integration helpers for LLM chat methods.

Eliminates copy-pasted memory retrieval / injection / storage patterns
that previously appeared in 4 places inside ``llm_service.py``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .background_tasks import spawn_background_task
from .evermem_config import EverMemConfig
from .evermem_service import EverMemService

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    """Carries the outcome of a memory preparation step."""

    service: EverMemService | None = None
    scope: str = "anonymous"
    group_id: str | None = None
    memories_retrieved: int = 0
    memory_saved: bool = False
    last_user_text: str | None = None


# ---------------------------------------------------------------------------
# 1. Extract last user message text
# ---------------------------------------------------------------------------

def extract_last_user_text(messages: list[dict[str, Any]]) -> str | None:
    """Return the text of the last ``user`` message.

    Handles both plain string content and multimodal list-of-parts content.
    """
    raw = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        None,
    )
    if raw is None:
        return None
    if isinstance(raw, list):
        text_parts = [
            p.get("text", "")
            for p in raw
            if isinstance(p, dict) and p.get("type") == "text"
        ]
        return " ".join(text_parts).strip() or None
    return str(raw).strip() or None


# ---------------------------------------------------------------------------
# 2. Two-stage memory search
# ---------------------------------------------------------------------------

async def search_memories_two_stage(
    service: EverMemService,
    query: str,
    user_id: str,
    group_id: str | None = None,
    min_score: float = 0.3,
) -> list[dict[str, Any]]:
    """Search EverMem with an optional group-scoped pass first."""
    memories: list[dict[str, Any]] = []
    if group_id:
        memories = await service.search_memories(
            query=query,
            user_id=user_id,
            group_ids=[group_id],
            min_score=min_score,
        )
    if not memories:
        memories = await service.search_memories(
            query=query,
            user_id=user_id,
            min_score=min_score,
        )
    return memories if isinstance(memories, list) else []


# ---------------------------------------------------------------------------
# 3. Prepare memory context + inject into messages
# ---------------------------------------------------------------------------

async def prepare_memory_context(
    messages: list[dict[str, Any]],
    *,
    use_memory: bool = True,
    request_headers: dict[str, Any] | None = None,
    use_two_stage: bool = False,
) -> MemoryContext:
    """Create EverMemConfig, retrieve memories, inject into *messages* in-place.

    Parameters
    ----------
    messages:
        The normalised message list (mutated in-place to inject memory context).
    use_memory:
        If ``False`` the whole step is skipped.
    request_headers:
        Optional HTTP headers carrying EverMem configuration.
    use_two_stage:
        If ``True`` uses group-scoped search first then global fallback.
        If ``False`` does a single-pass search (legacy non-streaming behaviour).
    """
    ctx = MemoryContext()

    if not use_memory:
        return ctx

    evermem_config = EverMemConfig()
    if request_headers:
        evermem_config.update_from_headers(request_headers)

    ctx.service = evermem_config.get_service()
    ctx.scope = evermem_config.memory_scope
    ctx.group_id = evermem_config.group_id or None

    if ctx.service is None:
        return ctx

    last_user_msg = extract_last_user_text(messages)
    ctx.last_user_text = last_user_msg
    if not last_user_msg:
        return ctx

    # --- store user message (fire-and-forget) ---
    add_kwargs: dict[str, Any] = {
        "content": last_user_msg,
        "user_id": ctx.scope,
    }
    if use_two_stage:
        # streaming paths include extra sender metadata
        add_kwargs.update(sender=ctx.scope, sender_name="User", group_id=ctx.group_id)
    spawn_background_task(ctx.service.add_memory(**add_kwargs))
    ctx.memory_saved = True

    # --- retrieve memories ---
    if ctx.service.should_skip_memory(last_user_msg):
        return ctx

    try:
        if use_two_stage:
            memories = await search_memories_two_stage(
                ctx.service, last_user_msg, ctx.scope, ctx.group_id,
            )
        else:
            memories = await ctx.service.search_memories(
                query=last_user_msg, user_id=ctx.scope,
            )

        if memories:
            ctx.memories_retrieved = len(memories)
            memory_context = "\n".join(
                m.get("content", "") for m in memories if isinstance(m, dict)
            )
            _inject_memory_into_messages(messages, memory_context)
    except Exception as exc:
        logger.error("Failed to retrieve memories: %s", exc)

    return ctx


def _inject_memory_into_messages(
    messages: list[dict[str, Any]],
    memory_text: str,
) -> None:
    """Append memory context to the system message (or insert one)."""
    memory_injection = f"\n\n【相关记忆】\n{memory_text}"
    sys_msg = next((m for m in messages if m.get("role") == "system"), None)
    if sys_msg:
        if isinstance(sys_msg["content"], str):
            sys_msg["content"] += memory_injection
    else:
        messages.insert(
            0,
            {"role": "system", "content": f"系统提示：请利用以下用户记忆完成对话。{memory_injection}"},
        )


# ---------------------------------------------------------------------------
# 4. Save assistant reply
# ---------------------------------------------------------------------------

def save_assistant_memory(
    ctx: MemoryContext,
    reply: str,
    *,
    reasoner=None,
) -> None:
    """Fire-and-forget save of the assistant reply.

    Parameters
    ----------
    ctx:
        The ``MemoryContext`` obtained from ``prepare_memory_context``.
    reply:
        The assistant response text.
    reasoner:
        Optional async callable ``(text: str, mode: str) -> str | None``
        used to refine the reply before storing (e.g. ``LLMService.reason_about_text``).
    """
    if not ctx.service or not reply:
        return

    if reasoner is not None:
        async def _save_refined(srv: EverMemService) -> None:
            refined = await reasoner(reply, mode="memory")
            content = refined if refined else reply
            await srv.add_memory(
                content=content,
                user_id=ctx.scope,
                sender=f"{ctx.scope}_assistant",
                sender_name="Assistant",
                group_id=ctx.group_id,
            )

        spawn_background_task(_save_refined(ctx.service))
    else:
        spawn_background_task(
            ctx.service.add_memory(
                content=reply,
                user_id=ctx.scope,
                sender_name="Assistant",
            )
        )

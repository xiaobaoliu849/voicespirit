"""Fire-and-forget 后台任务的统一管理。

直接 ``asyncio.create_task(coro)`` 却丢弃返回值有两个隐患：

1. 事件循环只对任务持有弱引用，任务可能在执行中途被垃圾回收；
2. 任务里抛出的异常无人 await，只会在 GC 时以
   "Task exception was never retrieved" 的形式出现，难以排查。

这里用一个模块级集合持有强引用，任务结束时自动移除并记录异常。
凡是不需要等待结果的 ``asyncio.create_task(...)``，都应改用
:func:`spawn_background_task`。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine

logger = logging.getLogger(__name__)

_BACKGROUND_TASKS: set["asyncio.Task[Any]"] = set()


def spawn_background_task(
    coro: Coroutine[Any, Any, Any],
    *,
    name: str | None = None,
) -> "asyncio.Task[Any]":
    """创建一个后台任务并持有强引用，结束后自动清理 + 记录异常。"""
    task = asyncio.create_task(coro, name=name)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_on_task_done)
    return task


def _on_task_done(task: "asyncio.Task[Any]") -> None:
    _BACKGROUND_TASKS.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.exception(
            "Background task %s raised an unhandled exception",
            task.get_name(),
            exc_info=exc,
        )

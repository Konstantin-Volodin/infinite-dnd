"""Shared agent loop helper."""
from __future__ import annotations

import json
import os
from typing import Any, Callable

from pydantic_ai import Agent

from ..core import ToolPlan


def run_loop(
    agent: Agent,
    user_msg: str,
    deps: Any,
    tool_executor: Callable | None,
    fallback_tool: str,
    fallback_args: dict | None = None,
    max_steps: int | None = None,
) -> dict:
    """Run the agent, optionally looping with tool execution until done or max_steps."""
    if tool_executor is None:
        plan: ToolPlan = agent.run_sync(user_msg, deps=deps).output
        if not plan.calls:
            return {"tool": fallback_tool, **(fallback_args or {})}
        first = plan.calls[0]
        return {
            "tool": first.tool,
            **first.arguments,
            "all_calls": [{"tool": c.tool, "arguments": c.arguments} for c in plan.calls],
        }

    max_steps = max_steps or int(os.getenv("GAME_MAX_ACTIONS_PER_TURN", "3"))
    all_calls: list[dict] = []
    all_results: list[dict] = []

    for _ in range(max_steps):
        msg = user_msg
        if all_results:
            history = "\n".join(json.dumps(r, default=str) for r in all_results)
            msg = f"{user_msg}\n\nPrevious tool results:\n{history}"

        plan = agent.run_sync(msg, deps=deps).output
        if not plan.calls:
            break

        for call in plan.calls:
            all_calls.append({"tool": call.tool, "arguments": call.arguments})
            all_results.append(tool_executor(call.tool, **call.arguments))

    if not all_calls:
        return {"tool": fallback_tool, **(fallback_args or {})}

    first = all_calls[0]
    return {
        "tool": first["tool"],
        **first["arguments"],
        "all_calls": all_calls,
        "all_results": all_results,
    }

"""Base agent helpers for tool-driven turns."""

import json
import os
from typing import Any, Callable, Dict, List, Optional

from ..core import LLMClient


class BaseAgent:
    """Base class with shared LLM interaction logic."""

    def __init__(self):
        self.llm = LLMClient()

    def _decide(
        self,
        system_prompt: str,
        context: str,
        tools: List[Dict[str, Any]],
        fallback_tool: str = "wait",
        fallback_args: Dict = None,
        require_tool: bool = False,
        tool_executor: Optional[Callable] = None,
        max_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make a decision using a typed plan response and optional tool execution."""
        if tool_executor is None:
            return self._decide_single(
                system_prompt, context, tools, fallback_tool, fallback_args, require_tool
            )

        if max_steps is None:
            max_steps = int(os.getenv("GAME_MAX_ACTIONS_PER_TURN", "3"))

        all_calls: List[Dict[str, Any]] = []
        all_results: List[Dict[str, Any]] = []

        for step in range(max_steps):
            prompt = self._build_prompt(system_prompt, context, tools, all_results)
            plan = self.llm.plan(prompt, self._build_context(context, all_results))

            if not plan.calls:
                break

            for call in plan.calls:
                call_entry = {"tool": call.tool, "arguments": call.arguments}
                all_calls.append(call_entry)

                tool_result = tool_executor(call.tool, **call.arguments)
                all_results.append(tool_result)

        if not all_calls:
            return {"tool": fallback_tool, **(fallback_args or {"reason": "No action taken"})}

        first_call = all_calls[0]
        return {
            "tool": first_call["tool"],
            **first_call["arguments"],
            "all_calls": all_calls,
            "all_results": all_results,
        }

    def _decide_single(
        self,
        system_prompt: str,
        context: str,
        tools: List[Dict[str, Any]],
        fallback_tool: str = "wait",
        fallback_args: Dict = None,
        require_tool: bool = False,
    ) -> Dict[str, Any]:
        """Single-step decision using the same typed plan path."""
        plan = self.llm.plan(self._build_prompt(system_prompt, context, tools, []), context)

        if not plan.calls:
            return {"tool": fallback_tool, **(fallback_args or {"reason": "No action taken"})}

        first_call = plan.calls[0]
        return {
            "tool": first_call.tool,
            **first_call.arguments,
            "all_calls": [{"tool": call.tool, "arguments": call.arguments} for call in plan.calls],
        }

    def _build_prompt(
        self,
        system_prompt: str,
        context: str,
        tools: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]],
    ) -> str:
        tool_lines = []
        for tool in tools:
            tool_lines.append(f"- {tool['name']}: {tool.get('description', '')}")

        prompt = (
            system_prompt
            + "\n\nReturn a JSON object with a `calls` array. Each call must include `tool` and `arguments`."
            + "\nOnly choose from these tools:\n"
            + "\n".join(tool_lines)
        )

        if all_results:
            prompt += "\n\nPrevious tool results are available in the user context."

        return prompt

    def _build_context(self, context: str, all_results: List[Dict[str, Any]]) -> str:
        if not all_results:
            return context

        history = "\n".join(json.dumps(result, default=str) for result in all_results)
        return f"{context}\n\nPrevious tool results:\n{history}"

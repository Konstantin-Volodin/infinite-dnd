"""
Base Agent - Shared functionality for all LLM agents.
"""

import os
import json
from typing import Dict, Any, List, Callable, Optional
from ...core.llm import LLMClient


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
        """Make a decision using LLM with tool calling.

        When tool_executor is provided, runs an agentic loop: call tools,
        feed results back to the LLM, repeat until the LLM yields (no tool
        calls) or max_steps is reached.

        When tool_executor is None, behaves as single-shot (backward compat).
        """
        if tool_executor is None:
            return self._decide_single(
                system_prompt, context, tools, fallback_tool, fallback_args, require_tool
            )

        if max_steps is None:
            max_steps = int(os.getenv("GAME_MAX_ACTIONS_PER_TURN", "3"))

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]
        all_calls: List[Dict[str, Any]] = []
        all_results: List[Dict[str, Any]] = []

        for step in range(max_steps):
            result = self.llm.chat_step(
                messages, tools, require_tool=(require_tool and step == 0)
            )

            if result["type"] == "error":
                print(f"Agent error: {result.get('message', 'Unknown error')}")
                break

            if result["type"] == "text":
                break

            # Append assistant message to conversation for threading
            messages.append(result["raw_message"])

            for call in result["calls"]:
                call_entry = {"tool": call["tool"], "arguments": call.get("arguments", {})}
                all_calls.append(call_entry)

                tool_result = tool_executor(call["tool"], **call.get("arguments", {}))
                all_results.append(tool_result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(tool_result, default=str),
                })

        if not all_calls:
            return {"tool": fallback_tool, **(fallback_args or {"reason": "No action taken"})}

        first_call = all_calls[0]
        action = {
            "tool": first_call["tool"],
            **first_call["arguments"],
            "all_calls": all_calls,
            "all_results": all_results,
        }
        return action

    def _decide_single(
        self,
        system_prompt: str,
        context: str,
        tools: List[Dict[str, Any]],
        fallback_tool: str = "wait",
        fallback_args: Dict = None,
        require_tool: bool = False,
    ) -> Dict[str, Any]:
        """Original single-shot decision (no agentic loop)."""
        result = self.llm.chat_with_tools(
            system_prompt, context, tools, require_tool=require_tool
        )

        if result["type"] == "tool_calls":
            first_call = result["calls"][0]
            tool_name = first_call["tool"]

            all_calls = []
            for call in result["calls"]:
                all_calls.append(
                    {"tool": call.get("tool"), "arguments": call.get("arguments", {})}
                )

            action = {
                "tool": tool_name,
                **first_call["arguments"],
                "all_calls": all_calls,
            }
            return action
        elif result["type"] == "text":
            content = result.get("content", "...")
            return {"tool": fallback_tool, "content": content}
        else:
            print(f"Agent error: {result.get('message', 'Unknown error')}")
            return {"tool": fallback_tool, **(fallback_args or {"reason": "Error"})}

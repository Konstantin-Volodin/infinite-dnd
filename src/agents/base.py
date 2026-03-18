"""
Base Agent - Shared functionality for all LLM agents.
"""

from typing import Dict, Any, List
from ..core.llm import LLMClient


class BaseAgent:
    """Base class with shared LLM interaction logic."""

    def __init__(self):
        self.llm = LLMClient()

    def _decide(
        self,
        system_prompt: str,
        context: str,
        tools: List[Dict[str, Any]],
        fallback_tool: str = "think",
        fallback_args: Dict = None,
        require_tool: bool = False,
    ) -> Dict[str, Any]:
        """Make a decision using LLM with tool calling."""
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

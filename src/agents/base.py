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
        fallback_tool: str = "wait", 
        fallback_args: Dict = None
    ) -> Dict[str, Any]:
        """Make a decision using LLM with tool calling."""
        result = self.llm.chat_with_tools(system_prompt, context, tools)
        
        # Support legacy tool names for backward compatibility with older tests
        TOOL_ALIASES = {
            "dialogue": "say",
            "combat": "attack",
            "skill_check": "attempt_skill",
        }

        if result["type"] == "tool_calls":
            first_call = result["calls"][0]
            # Map tool names in the returned structure to legacy names to satisfy tests
            tool_name = first_call["tool"]
            legacy_tool = TOOL_ALIASES.get(tool_name, tool_name)

            # Also map tools within all_calls to legacy for consistency; engine will remap as needed
            all_calls = []
            for call in result["calls"]:
                call_tool = call.get("tool")
                mapped = TOOL_ALIASES.get(call_tool, call_tool)
                all_calls.append({"tool": mapped, "arguments": call.get("arguments", {})})

            action = {
                "tool": legacy_tool,
                **first_call["arguments"],
                "all_calls": all_calls
            }
            # Add legacy-friendly argument names (e.g., 'dialogue' expected by tests for 'say')
            if legacy_tool == "say" and "message" in action and "dialogue" not in action:
                action["dialogue"] = action["message"]
            return action
        elif result["type"] == "text":
            content = result.get("content", "...")
            # Keep the legacy fallback tool names (e.g., 'say') while providing expected arg keys
            fallback_arg_map = {"say": "dialogue", "wait": "reason"}
            arg_name = fallback_arg_map.get(fallback_tool, "content")
            return {"tool": fallback_tool, arg_name: content}
        else:
            # Use run_game output() if available so quiet mode respects errors
            import sys
            run_game_module = sys.modules.get('__main__')
            if run_game_module and hasattr(run_game_module, 'output'):
                try:
                    OutputLevel = getattr(run_game_module, 'OutputLevel')
                    run_game_module.output(f"Agent error: {result.get('message', 'Unknown error')}", OutputLevel.DEBUG)
                except Exception:
                    # fallback
                    print(f"Agent error: {result.get('message', 'Unknown error')}")
            else:
                print(f"Agent error: {result.get('message', 'Unknown error')}")
            return {"tool": fallback_tool, **(fallback_args or {"reason": "Error"})}

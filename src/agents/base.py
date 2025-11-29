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
        
        if result["type"] == "tool_calls":
            first_call = result["calls"][0]
            return {
                "tool": first_call["tool"],
                **first_call["arguments"],
                "all_calls": result["calls"]
            }
        elif result["type"] == "text":
            content = result.get("content", "...")
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

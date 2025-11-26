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
            # Return the first tool call for backward compatibility
            # Agents that support multiple calls should handle the raw result
            first_call = result["calls"][0]
            return {
                "tool": first_call["tool"],
                **first_call["arguments"],
                "all_calls": result["calls"] # Pass all calls for advanced agents
            }
        elif result["type"] == "tool_call":
            # Legacy single tool call support
            return {
                "tool": result["tool"],
                **result["arguments"]
            }
        elif result["type"] == "text":
            # LLM didn't use tools, use fallback
            content = result.get("content", "...")
            # Map to appropriate argument based on fallback tool
            if fallback_tool == "say":
                return {"tool": "say", "dialogue": content}
            elif fallback_tool == "wait":
                return {"tool": "wait", "reason": content}
            else:
                return {"tool": fallback_tool, "content": content}
        else:
            # Error case
            print(f"Agent error: {result.get('message', 'Unknown error')}")
            return {
                "tool": fallback_tool,
                **(fallback_args or {"reason": "Error"})
            }

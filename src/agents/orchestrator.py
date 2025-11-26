"""
Orchestrator Agent - Decides turn order and pacing.
"""
from typing import Dict, Any
from .base import BaseAgent
from ..core.models import WorldState
from ..prompts import build_orchestrator_system_prompt, build_orchestrator_context
from ..tools import get_orchestrator_tools


class OrchestratorAgent(BaseAgent):
    """Decides who should act next based on the current scene."""
    
    def decide_next_actor(self, state: WorldState) -> Dict[str, Any]:
        """Returns who should act next and why."""
        result = self._decide(
            system_prompt=build_orchestrator_system_prompt(),
            context=build_orchestrator_context(state),
            tools=get_orchestrator_tools(),
            fallback_tool="select_next_actor",
            fallback_args={"actor": "dm", "reason": "Fallback - orchestrator didn't respond"}
        )
        
        # Handle multiple tool calls (e.g. update_narrative + select_next_actor)
        if "all_calls" in result:
            narrative_update = None
            actor_selection = None
            
            for call in result["all_calls"]:
                if call["tool"] == "update_narrative":
                    narrative_update = call["arguments"]
                elif call["tool"] == "select_next_actor":
                    actor_selection = call["arguments"]
            
            # If we found an actor selection, return it with narrative update attached
            if actor_selection:
                return {
                    "tool": "select_next_actor",
                    **actor_selection,
                    "narrative_update": narrative_update
                }
        
        # Fallback for single tool call or error
        if result["tool"] == "select_next_actor":
            return result
        elif result["tool"] == "update_narrative":
            # If only narrative was updated, default to DM
            return {
                "actor": "dm",
                "reason": "Narrative updated, DM should narrate",
                "suggested_action": "Reflect the new scene mood.",
                "narrative_update": result
            }
        else:
            return {
                "actor": "dm",
                "reason": "Fallback - orchestrator error"
            }

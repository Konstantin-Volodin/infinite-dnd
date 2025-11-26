"""
Director Agent - Decides turn order and pacing.
"""
from typing import Dict, Any
from .base import BaseAgent
from ..core.models import WorldState
from ..prompts import build_director_system_prompt, build_director_context
from ..tools import get_director_tools


class DirectorAgent(BaseAgent):
    """Decides who should act next based on the current scene."""
    
    def decide_next_actors(self, state: WorldState) -> Dict[str, Any]:
        """Returns a sequence of actors to act and why."""
        result = self._decide(
            system_prompt=build_director_system_prompt(),
            context=build_director_context(state),
            tools=get_director_tools(),
            fallback_tool="plan_sequence",
            fallback_args={"sequence": [{"actor": "dm", "suggested_action": "Advance the story."}]}
        )
        
        # Handle plan_sequence tool
        if result["tool"] == "plan_sequence":
            sequence = result.get("sequence", [])
            # Parse sequence if it's a string (JSON)
            if isinstance(sequence, str):
                import json
                try:
                    sequence = json.loads(sequence)
                except:
                    sequence = []
            
            return {
                "sequence": sequence if sequence else [{"actor": "dm", "suggested_action": "Advance the story."}],
                "situation_summary": result.get("situation_summary", ""),
                "narrative_update": {
                    "scene_type": result.get("scene_type"),
                    "tension": result.get("tension")
                } if result.get("scene_type") else None
            }
        
        # Fallback
        return {
            "sequence": [{"actor": "dm", "suggested_action": "Advance the story."}],
            "narrative_update": None
        }

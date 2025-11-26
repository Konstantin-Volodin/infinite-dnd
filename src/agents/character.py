"""
Character Agent - Controls player and NPC characters.
"""
from typing import Dict, Any
from .base import BaseAgent
from ..core.models import WorldState
from ..prompts import build_character_system_prompt, build_character_context
from ..tools import get_character_tools


class CharacterAgent(BaseAgent):
    """Agent that controls a single character (PC or NPC)."""
    
    def __init__(self, character_id: str):
        super().__init__()
        self.character_id = character_id

    def decide_action(self, state: WorldState, guidance: str = "") -> Dict[str, Any]:
        """Decide what action this character should take.
        
        Args:
            guidance: Optional suggestion from the orchestrator about what to do.
        """
        char = state.characters.get(self.character_id)
        if not char:
            return {"tool": "wait", "reason": "Character not found"}
        
        context = build_character_context(char, state)
        if guidance:
            context = f"{guidance}\n\n{context}"
        
        action = self._decide(
            system_prompt=build_character_system_prompt(char),
            context=context,
            tools=get_character_tools(),
            fallback_tool="say"
        )
        
        # Ensure character_id is attached
        if "character_id" not in action:
            action["character_id"] = self.character_id
            
        return action

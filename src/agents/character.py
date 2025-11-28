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
            guidance: Optional suggestion from the director about what to do.
        """
        char = state.characters.get(self.character_id)
        if not char:
            return {"tool": "wait", "reason": "Character not found"}
        
        context = build_character_context(char, state)
        if guidance:
            context = f"{guidance}\n\n{context}"
        
        action = self._decide(
            system_prompt=build_character_system_prompt(char) + "\n\nYou can use many tools simultaneously and should output all tool calls in 1 response.",
            context=context,
            tools=get_character_tools(),
            fallback_tool="say"
        )
        
        # Ensure character_id is attached
        if "character_id" not in action:
            action["character_id"] = self.character_id
        # Precompute local references
        loc = state.locations.get(char.location_id)
        # Validate basic target coherence and re-request action if invalid (simple fix)
        def _is_valid_action(a: Dict[str, Any]) -> bool:
            tool = a.get("tool")
            loc = state.locations.get(char.location_id)
            present_names = [c.name for c in state.characters.values() if c.location_id == char.location_id and c.id != char.id]
            if tool == "say":
                tgt = a.get("target")
                if tgt and tgt not in present_names:
                    return False
            if tool == "examine":
                # Check if location exists before accessing features
                if not loc:
                    return False
                tgt = a.get("target") or a.get("examine_target")
                features = [f for f in (loc.features or [])]
                items = [i for i in (loc.items or [])]
                inv = [i for i in (char.inventory or [])]
                
                # Allow if target is in features/items/inventory
                if tgt and (tgt in features or tgt in items or tgt in inv):
                    return True
                
                # Strict validation: Only allow if target is in features/items/inventory
                if tgt and (tgt in features or tgt in items or tgt in inv):
                    return True
                
                # Otherwise invalid
                if tgt:
                    return False
            if tool == "move":
                # require destination be a connected location or existing loc name
                dest = a.get("destination") or a.get("location_id")
                if dest:
                    found = any(dest.lower() in lid.lower() or dest.lower() in l.name.lower() for lid, l in state.locations.items())
                    if not found:
                        return False
            return True
        # If initial action invalid, re-run once with clarified guidance
        if not _is_valid_action(action):
            allowed_say = [c.name for c in state.characters.values() if c.location_id == char.location_id and c.id != char.id]
            allowed_examine = list(((loc.features or []) + (loc.items or []) + (char.inventory or [])) if loc else (char.inventory or []))
            new_guidance = guidance + f"\n\nNOTE: Your previous action targeted something invalid. Allowed say targets: {allowed_say}. Allowed examine targets: {allowed_examine}. Use 'move' to go to other locations."
            action = self._decide(
                system_prompt=build_character_system_prompt(char) + "\n\nYou can use many tools simultaneously and should output all tool calls in 1 response.",
                context=new_guidance + "\n\n" + context,
                tools=get_character_tools(),
                fallback_tool="say"
            )
            if "character_id" not in action:
                action["character_id"] = self.character_id
        # Convert 'move' to a local feature into an 'examine' if the destination is a feature of the current location
        if action.get("tool") == "move":
            dest = action.get("destination") or action.get("location_id")
            # If the destination matches a feature in the current location, switch to examine
            if loc:
                feature_names = [f for f in (loc.features or [])]
                if dest and any(dest.lower() in f.lower() or f.lower() in dest.lower() for f in feature_names):
                    action = {"tool": "examine", "target": dest, "character_id": self.character_id}
            
        return action

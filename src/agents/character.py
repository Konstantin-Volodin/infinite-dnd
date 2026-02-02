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
            return {"tool": "think", "reason": "Character not found"}

        context = build_character_context(char, state)
        if guidance:
            context = f"{guidance}\n\n{context}"

            action = self._decide(
            system_prompt=build_character_system_prompt(char)
            + "\n\nYou can use many tools simultaneously and should output all tool calls in 1 response.",
            context=context,
            tools=get_character_tools(),
            fallback_tool="think",
            require_tool=False,  # Allow natural prose introspection sometimes
        )

        # Ensure character_id is attached
        if "character_id" not in action:
            action["character_id"] = self.character_id

        # Precompute local references
        loc = state.locations.get(char.location)

        # Validate basic target coherence and re-request action if invalid (simple fix)
        def _is_valid_action(a: Dict[str, Any]) -> bool:
            tool = a.get("tool")
            if tool == "move":
                # require destination be a connected location or existing loc name
                dest = a.get("location")
                if dest:
                    # Prevent moving to current location
                    if dest == char.location or (loc and dest == loc.id):
                        return False

                    found = any(
                        dest.lower() in lid.lower() or dest.lower() in loc.id.lower()
                        for lid, loc in state.locations.items()
                    )
                    if not found:
                        return False
            return True

        # If initial action invalid, re-run once with clarified guidance
        if not _is_valid_action(action):
            new_guidance = (
                guidance
                + "\n\nNOTE: Your previous action targeted something invalid. You cannot move to your current location. Use 'move' to go to CONNECTED locations."
            )
            action = self._decide(
                system_prompt=build_character_system_prompt(char)
                + "\n\nYou can use many tools simultaneously and should output all tool calls in 1 response.",
                context=new_guidance + "\n\n" + context,
                tools=get_character_tools(),
                fallback_tool="think",
            )
            if "character_id" not in action:
                action["character_id"] = self.character_id

        # Normalize target references: if an id was returned for a target, map to name for test expectations
        if "target" in action:
            t = action["target"]
            if isinstance(t, str):
                # Support returned ids like 'char.id-char-1' or plain 'char-1'
                normalized_t = t.replace("char.id-", "")
                if normalized_t in state.characters:
                    action["target"] = state.characters[normalized_t].id

        # Normalize all_calls target fields too
        if "all_calls" in action:
            for call in action["all_calls"]:
                args = call.get("arguments", {})
                if "target" in args and isinstance(args["target"], str):
                    normalized_args_t = args["target"].replace("char.id-", "")
                    if normalized_args_t in state.characters:
                        args["target"] = state.characters[normalized_args_t].id

        return action

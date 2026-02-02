"""
Director Agent - Decides turn order and pacing.
"""

from typing import Dict, Any, List
from .base import BaseAgent
from ..core.models import WorldState, CharacterType
from ..prompts import build_director_system_prompt, build_director_context
from ..tools import get_director_tools


class DirectorAgent(BaseAgent):
    """Decides who should act next based on the current scene."""

    def decide_next_actors(self, state: WorldState) -> List[Dict[str, str]]:
        """Returns a sequence of actors with guidance."""
        result = self._decide(
            system_prompt=build_director_system_prompt(),
            context=build_director_context(state),
            tools=get_director_tools(),
            fallback_tool="direct",
            fallback_args={"actor": "dm", "guidance": "Advance the story."},
        )

        # Collect all direct calls into sequence
        sequence = []
        calls = result.get("all_calls", [{"tool": result.get("tool"), "arguments": result}])
        
        for call in calls:
            if call.get("tool") == "direct":
                args = call.get("arguments", call)
                sequence.append({
                    "actor": args.get("actor", "dm"),
                    "guidance": args.get("guidance", ""),
                })

        # Default to first PC if empty
        if not sequence:
            first_pc = next(
                (cid for cid, c in state.characters.items() if c.type == CharacterType.PC),
                "dm",
            )
            sequence = [{"actor": first_pc, "guidance": "Continue exploring."}]

        return sequence

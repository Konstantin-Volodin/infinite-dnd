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
            system_prompt=build_director_system_prompt() + "\n\nYou can use many tools simultaneously to plan a sequence.",
            context=build_director_context(state),
            tools=get_director_tools(),
            fallback_tool="select_next_actor",
            fallback_args={"actor": "dm", "character_thinking": "Advance the story."}
        )
        
        # Collect all actor selections from tool calls
        sequence = []
        narrative_update = {}
        
        # Check if there are multiple tool calls
        if "all_calls" in result:
            for call in result["all_calls"]:
                tool_name = call.get("tool")
                args = call.get("arguments", {})
                
                if tool_name == "select_next_actor":
                    sequence.append({
                        "actor": args.get("actor", "dm"),
                        "character_thinking": args.get("character_thinking", ""),
                        "reason": args.get("reason", "")
                    })
                elif tool_name == "update_narrative":
                    if args.get("scene_type"):
                        narrative_update["scene_type"] = args["scene_type"]
                    if args.get("tension"):
                        narrative_update["tension"] = args["tension"]
                elif tool_name == "scene_transition":
                    narrative_update["scene_transition"] = {
                        "target_location_id": args.get("target_location_id"),
                        "character_ids": args.get("character_ids", [])
                    }
                    # Also add DM narration as first actor
                    sequence.insert(0, {
                        "actor": "dm",
                        "character_thinking": f"Describe the arrival at {args.get('target_location_id')}. {args.get('narration_guidance', '')}",
                        "reason": "Scene transition"
                    })
        else:
            # Single call fallback - handle old plan_sequence for backwards compat
            tool_name = result.get("tool")
            
            if tool_name == "select_next_actor":
                sequence.append({
                    "actor": result.get("actor", "dm"),
                    "character_thinking": result.get("character_thinking", ""),
                    "reason": result.get("reason", "")
                })
            elif tool_name == "update_narrative":
                if result.get("scene_type"):
                    narrative_update["scene_type"] = result["scene_type"]
                if result.get("tension"):
                    narrative_update["tension"] = result["tension"]
            elif tool_name == "scene_transition":
                narrative_update["scene_transition"] = {
                    "target_location_id": result.get("target_location_id"),
                    "character_ids": result.get("character_ids", [])
                }
                sequence.append({
                    "actor": "dm",
                    "character_thinking": f"Describe the arrival at {result.get('target_location_id')}. {result.get('narration_guidance', '')}",
                    "reason": "Scene transition"
                })
            elif tool_name == "plan_sequence":
                # Backwards compatibility with old tool
                seq = result.get("sequence", [])
                if isinstance(seq, str):
                    import json
                    try:
                        seq = json.loads(seq)
                    except:
                        seq = []
                for item in seq:
                    sequence.append({
                        "actor": item.get("actor", "dm"),
                        "character_thinking": item.get("suggested_action", ""),
                        "reason": ""
                    })
                if result.get("scene_type"):
                    narrative_update["scene_type"] = result["scene_type"]
                if result.get("tension"):
                    narrative_update["tension"] = result["tension"]
        
        if not sequence:
            # Don't default to DM - select the first PC instead
            from ..core.models import CharacterType
            first_pc = next((char_id for char_id, char in state.characters.items() if char.type == CharacterType.PC), "dm")
            sequence = [{"actor": first_pc, "character_thinking": "Continue exploring.", "reason": "Director didn't select anyone"}]
        
        return {
            "sequence": sequence,
            "narrative_update": narrative_update if narrative_update else None
        }

"""
Tool Definitions - JSON schemas for LLM function calling.
"""
from typing import List, Dict, Any


def _tool(name: str, desc: str, params: Dict[str, str], required: List[str] = None) -> Dict:
    props = {k: {"type": "string", "description": v} for k, v in params.items()}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required if required is not None else list(params.keys())
            }
        }
    }


CHARACTER_TOOLS = [
    _tool("say", "Speak in character. PREFERRED when others are present.", {"content": "What to say."}),
    _tool("examine", "Examine something closely - a feature, person, item, or your surroundings. Use this to investigate mysteries and discover clues.", {"target": "What to examine (e.g., 'hidden passage', 'strange symbol', 'the merchant')."}),
    _tool("move", "Move to a different location. Only use this when you have a clear reason to leave.", {"location_id": "Must be a location ID from the list."}),
    _tool("pickup", "Pick up an item from the ground.", {"item_name": "Item name."}),
    _tool("use", "Use an item on something.", {"item_name": "Item to use.", "target": "What to use it on."}),
    _tool("attempt_skill", "Attempt a difficult action using a skill. Use this when the outcome is uncertain.", {
        "skill": "The skill to use (e.g., 'stealth', 'investigation', 'persuasion', 'athletics').",
        "action_description": "What you are trying to do (e.g., 'I try to pick the lock', 'I search for hidden traps')."
    }),
    _tool("attack", "Attack a target to start combat.", {"target": "Who to attack.", "weapon": "Weapon to use (or 'unarmed')."}),
    _tool("wait", "Do nothing. Only use when there's nothing meaningful to do.", {"reason": "Reason."}, required=[]),
]

DM_TOOLS = [
    _tool("narrate", "Narrate.", {"content": "Narration."}),
    _tool("spawn_event", "Create event.", {"location_id": "Location.", "description": "Event."}),
    _tool("update_quest", "Update quest.", {"quest_id": "Quest.", "status": "Status."}, required=["quest_id", "status"]),
    _tool("create_location", "Create location.", {"name": "Name.", "description": "Desc.", "connected_from": "From."}),
    _tool("create_item", "Create item.", {"item_name": "Item.", "location_id": "Location."}),
    _tool("spawn_npc", "Create a new NPC character.", {
        "npc_id": "Unique ID (lowercase, no spaces, e.g. 'guard-marcus').",
        "name": "Display name (e.g. 'Marcus the Guard').",
        "role": "Their role/class (e.g. 'guard', 'merchant', 'thief').",
        "location_id": "Where they appear.",
        "description": "Brief backstory/personality.",
        "goal": "What they want (optional)."
    }, required=["npc_id", "name", "role", "location_id", "description"]),
    _tool("remove_npc", "Remove an NPC from the game (died, left, etc.).", {
        "npc_id": "ID of the NPC to remove.",
        "reason": "Why (for narration)."
    }),
]

DIRECTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "plan_sequence",
            "description": "Plan a sequence of actors to act in order. This creates a mini-arc of actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "situation_summary": {"type": "string", "description": "Brief summary of what just happened and what's at stake."},
                    "scene_type": {"type": "string", "enum": ["exploration", "social", "combat", "investigation"], "description": "The current mode of gameplay."},
                    "tension": {"type": "string", "enum": ["low", "rising", "high"], "description": "The current dramatic tension level."},
                    "sequence": {
                        "type": "array",
                        "description": "List of actors to act in order",
                        "items": {
                            "type": "object",
                            "properties": {
                                "actor": {"type": "string", "description": "Actor ID (character_id or 'dm')"},
                                "suggested_action": {"type": "string", "description": "What the actor SHOULD do. Be specific."}
                            },
                            "required": ["actor", "suggested_action"]
                        }
                    }
                },
                "required": ["situation_summary", "sequence"]
            }
        }
    }
]


def get_character_tools() -> List[Dict[str, Any]]:
    return CHARACTER_TOOLS

def get_dm_tools() -> List[Dict[str, Any]]:
    return DM_TOOLS

def get_director_tools() -> List[Dict[str, Any]]:
    return DIRECTOR_TOOLS

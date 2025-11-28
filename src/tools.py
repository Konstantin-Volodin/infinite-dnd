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
    _tool("say", "Speak in character.", {"content": "What to say."}),
    _tool("examine", "Examine something closely - a feature, person, item, or your surroundings. Use this to investigate mysteries and discover clues.", {"target": "What to examine (e.g., 'hidden passage', 'strange symbol', 'the merchant')."}),
    _tool("move", "Move to a different location. Only use this when you have a clear reason to leave.", {"location_id": "Must be a location ID from the list."}),
    _tool("pickup", "Pick up an item from the ground.", {"item_name": "Item name."}),
    _tool("use", "Use an item on something. If using a spell or magical item, include 'spell_name' and a short effect description.", {"item_name": "Item to use.", "target": "What to use it on.", "spell_name": "Optional spell/item name if this is a magical use."}),
    _tool("attempt_skill", "Attempt a difficult action using a skill. Use this when the outcome is uncertain.", {
        "skill": "The skill to use (e.g., 'stealth', 'investigation', 'persuasion', 'athletics').",
        "action_description": "What you are trying to do (e.g., 'I try to pick the lock', 'I search for hidden traps')."
    }),
    _tool("attack", "Attack a target to start combat. Include a concise 'style' describing the movement (e.g., 'overhead slash', 'riposte', 'cleave').", {"target": "Who to attack.", "weapon": "Weapon to use (or 'unarmed').", "style": "Attack style or movement (optional)."}),
    
    # Self-modification tools
    _tool("update_knowledge", "Save new information you've learned.", {
        "knowledge_item": "What you learned (one fact)."
    }),
    _tool("reflect", "Update your current motivation or emotional state.", {
        "new_motivation": "What drives you right now.",
        "reason": "Why this changed (optional)."
    }, required=["new_motivation"]),
    _tool("add_memory", "Record a significant event or realization.", {
        "memory": "What happened or what you realized.",
        "importance": "high, medium, or low"
    }),
    
    # World modification tools
    _tool("create_small_item", "Attempt to create a small mundane item.", {
        "item_name": "Name of item to create (e.g., 'crude map', 'scribbled note').",
        "description": "Brief description of the item."
    }),
    _tool("modify_feature", "Attempt to alter a location feature.", {
        "feature": "Feature to modify (must exist).",
        "modification": "How you're changing it (e.g., 'barricade the door', 'extinguish the candle')."
    }),
    _tool("steal", "Covertly take an item. Requires stealth.", {
        "item_name": "Item to steal.",
        "target": "Who you're stealing from (or 'from the location')."
    }),
    _tool("hide_item", "Hide an item from view.", {
        "item_name": "Item to hide.",
        "location": "Where to hide it (e.g., 'under the table', 'in my cloak')."
    }),
    
    # Item lifecycle management
    _tool("destroy_item", "Destroy or discard an item permanently.", {
        "item_name": "Item to destroy.",
        "method": "How you destroy it (e.g., 'burn', 'smash', 'throw away')."
    }),
    _tool("consume_item", "Use and consume an item (removes it).", {
        "item_name": "Item to consume (food, potion, scroll).",
        "effect": "What happens when consumed (optional)."
    }),
    _tool("drop_item", "Drop an item from inventory to current location.", {
        "item_name": "Item to drop."
    }),
    
    _tool("wait", "Do nothing. Only use when there's nothing meaningful to do.", {"reason": "Reason."}, required=[]),
]

DM_TOOLS = [
    _tool("narrate", "Narrate.", {"content": "Narration."}),
    _tool("spawn_event", "[DEPRECATED - use narrate + new_features instead] Create ephemeral event.", {"location_id": "Location.", "description": "Event."}),
    _tool("update_quest", "Update quest.", {"quest_id": "Quest.", "status": "Status."}, required=["quest_id", "status"]),
    _tool("create_location", "Create location.", {"name": "Name.", "description": "Desc.", "connected_to": "Connections (to be added)."}),
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
            "name": "scene_transition",
            "description": "Move characters to a new location to change the scene.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_location_id": {"type": "string", "description": "ID of the location to move to."},
                    "character_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of character IDs to move."
                    },
                    "narration_guidance": {"type": "string", "description": "Guidance for the DM on how to describe the arrival."}
                },
                "required": ["target_location_id", "character_ids", "narration_guidance"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "select_next_actor",
            "description": "Select the next actor to act. Call this multiple times to plan a sequence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "actor": {"type": "string", "description": "character_id or 'dm'"},
                    "character_thinking": {"type": "string", "description": "Thought process of the character - use this to guide the character's action. Frame as internal monologue."},
                    "reason": {"type": "string", "description": "Why this actor should act now (for logging)."}
                },
                "required": ["actor", "character_thinking"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_narrative",
            "description": "Update scene metadata (type and tension).",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_type": {"type": "string", "enum": ["exploration", "social", "combat", "investigation"], "description": "Current game mode."},
                    "tension": {"type": "string", "enum": ["low", "high"], "description": "Current tension level."}
                },
                "required": []
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

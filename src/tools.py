"""
Tool Definitions - JSON schemas for LLM function calling.
"""
from typing import List, Dict, Any, Optional


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
    # game
    _tool("skill_check", "Describe what you will do next to advance the story. This can be an action (eg, pick a lock, climb a wall, attempt a persuasion, knowledge check, etc.). Use this when the outcome is uncertain.", {
        "skill": "the appropriate skill (e.g., 'stealth', 'investigation', 'persuasion', 'athletics').",
        "description": "What you are trying to do (e.g., 'I try to pick the lock', 'I attempt to scale this wall, there is no other way to past the city guards.').",
        "item_name": "Item to use (optional). Using items may impact the outcome of the skill check. you can decide how. THIS IS THE ONLY WAY TO USE ITEMS.",
    }),
    _tool("dialogue", "write a message to express thoughts, feelings, or observations. This can be spoken, narrated, or shouted. It can be a dialogue or a reaction to context. ", {
        "character_id": "your character id.",
        "message": "The content of the expression (e.g., 'Hello!', 'I see a strange light.', 'A chill ran down my spine.')."
    }),
    _tool("combat", "Start combat or help a character in combat. Describe the action and its impact.", {
        "target": "character-id.",
        "description": "Describe the action and its impact (e.g., 'As i chased after the thief, I threw one of my daggers, grazing his shoulder.').",
        "dmg?": "The damage dealt (e.g., '1d6 + 2').",
        "heal?": "The healing dealt (e.g., '1d6 + 2')."
    }),
    _tool("move", "Move to a different location. ONLY ALLOWED TO USE WHEN NO OTHER TOOLS ARE USED", {"location_id": "location ID chosen from options provided by the context."}),

    # Self-modification tools
    _tool("update", "update your state.", {
        "goals": "your current goals (optional for npcs)",
        "emotions": "your current emotional state (optional for npcs)",
        "knowledge": "your scratchpad, you can update it here with new information or memories triggered by recent events or observations.",
    }),
    
    # meta tools
    _tool("request", "request something from the DM.", {
        "request": "If there is nothing to do, if you are confused about something, or if you need help, you can use this tool to ask the DM for help. Maybe you want more money, or you want to know more about something. describe what you want.",
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

def get_dm_tools(scene_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return a list of tools available to the DM.

    If `scene_type` is provided and equals 'investigation', return a restricted
    subset that prevents the DM from spawning or removing NPCs (keeps the scene
    focused on narration and minor world modifications).
    """
    if scene_type == "investigation":
        allowed = {"narrate", "create_item", "create_location", "update_quest"}
        return [t for t in DM_TOOLS if t["function"]["name"] in allowed]
    return DM_TOOLS

def get_director_tools() -> List[Dict[str, Any]]:
    return DIRECTOR_TOOLS

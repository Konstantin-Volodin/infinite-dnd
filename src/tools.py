"""Tool definitions — JSON schemas for LLM function calling.

Character: act, speak, move (3)
DM: narrate, create, modify (3)
"""

from typing import List, Dict, Any


def _tool(
    name: str, desc: str, params: Dict[str, Any], required: List[str] = None
) -> Dict:
    """Build an OpenAI function-calling tool schema."""
    props = {}
    for k, v in params.items():
        if isinstance(v, str):
            props[k] = {"type": "string", "description": v}
        else:
            props[k] = v
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required if required is not None else list(params.keys()),
            },
        },
    }


# =============================================================================
# CHARACTER TOOLS (3)
# =============================================================================

CHARACTER_TOOLS = [
    _tool(
        "act",
        "Do something physical: attack, examine, pick up, use an item, cast a spell, sneak, climb — anything that isn't talking or traveling.",
        {
            "character_id": "Your character ID.",
            "description": "What you do.",
            "skill": "Skill for uncertain outcomes (e.g. 'stealth', 'athletics').",
            "target": "Who or what you interact with.",
        },
        required=["character_id", "description"],
    ),
    _tool(
        "speak",
        "Say something out loud. Include emotion and body language in your message.",
        {
            "character_id": "Your character ID.",
            "message": "What you say — full dialogue with tone and body language.",
            "target": "Who you're speaking to.",
        },
        required=["character_id", "message"],
    ),
    _tool(
        "move",
        "Travel to a connected location. Must be a valid exit from your current location.",
        {
            "character_id": "Your character ID.",
            "location": "Location ID to move to.",
        },
        required=["character_id", "location"],
    ),
]


# =============================================================================
# DM TOOLS (3)
# =============================================================================

DM_TOOLS = [
    _tool(
        "narrate",
        "Describe what happens in the world. Never write dialogue or thoughts for characters — they speak for themselves.",
        {
            "content": "The narration.",
            "prompts_character": "Character ID who should respond next (soft hint).",
        },
        required=["content"],
    ),
    _tool(
        "create",
        "Add a location, item, or NPC to the world.",
        {
            "type": {
                "type": "string",
                "enum": ["location", "item", "npc"],
                "description": "What to create.",
            },
            "id": "Unique ID (lowercase-hyphenated).",
            "name": "Display name.",
            "description": "Description or backstory.",
            "location": "Where it appears (required for item/npc).",
            "role": "NPC role (e.g. 'guard', 'merchant'). NPCs only.",
            "goal": "NPC motivation. NPCs only.",
        },
        required=["type", "name", "description"],
    ),
    _tool(
        "modify",
        "Change or remove something: update a quest, remove an NPC, update a location.",
        {
            "action": {
                "type": "string",
                "enum": ["update_quest", "remove_npc", "update_location"],
                "description": "What to do.",
            },
            "target_id": "ID of the quest, NPC, or location.",
            "status": "New status (quests: active/completed/failed).",
            "reason": "Why this change is happening.",
        },
        required=["action", "target_id"],
    ),
]


# =============================================================================
# GETTERS
# =============================================================================


def get_character_tools() -> List[Dict[str, Any]]:
    return CHARACTER_TOOLS


def get_dm_tools() -> List[Dict[str, Any]]:
    return DM_TOOLS

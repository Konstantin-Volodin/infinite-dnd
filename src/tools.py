"""
Tool Definitions - JSON schemas for LLM function calling.

Minimalist tool set:
- Character: act, speak, move, think (4)
- DM: narrate, create, modify (3)
- Director: direct (1)
- Storyteller: scene, decision_point, transition (3)
"""

from typing import List, Dict, Any


def _tool(
    name: str, desc: str, params: Dict[str, Any], required: List[str] = None
) -> Dict:
    """Helper to build OpenAI function-calling tool schema."""
    props = {}
    for k, v in params.items():
        if isinstance(v, str):
            props[k] = {"type": "string", "description": v}
        else:
            props[k] = v  # Allow full property definitions
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
# CHARACTER TOOLS (4)
# =============================================================================

CHARACTER_TOOLS = [
    _tool(
        "act",
        "Perform a physical action. Covers combat, examining, picking up items, using items, skill checks, casting spells, etc.",
        {
            "description": "What you do (e.g., 'attack the guard', 'examine the runes', 'pick up the lantern').",
            "skill": "Skill involved if uncertain outcome (e.g., 'stealth', 'athletics'). Optional.",
            "target": "Who/what you interact with. Optional.",
        },
        required=["description"],
    ),
    _tool(
        "speak",
        "Say something out loud. Use full sentences with emotion and body language. Example: '*leaning forward* Listen, I know this is hard to hear, but your brother was seen near the cellar that night.'",
        {
            "message": "What you say — full dialogue with tone, emotion, body language. Not fragments.",
            "target": "Who you're speaking to. Optional.",
        },
        required=["message"],
    ),
    _tool(
        "move",
        "Travel to a connected location.",
        {"location": "The location to move to (must be an available exit)."},
        required=["location"],
    ),
    _tool(
        "think",
        "Record internal changes AFTER acting or learning. Not for planning. Use sparingly.",
        {
            "goals": "Updated goals (only if they changed). Optional.",
            "emotions": "Emotional shift after an event. Optional.",
            "knowledge": "New fact to remember. Optional.",
        },
        required=[],
    ),
]


# =============================================================================
# DM TOOLS (3)
# =============================================================================

DM_TOOLS = [
    _tool(
        "narrate",
        "Describe the environment, action outcomes, and transitions. Do NOT speak for NPCs — they have their own turns.",
        {"content": "The narration text."},
        required=["content"],
    ),
    _tool(
        "create",
        "Add something new to the world: a location, item, or NPC.",
        {
            "type": {
                "type": "string",
                "enum": ["location", "item", "npc"],
                "description": "What to create.",
            },
            "id": "Unique ID (lowercase, hyphens, e.g., 'guard-marcus', 'dark-alley').",
            "name": "Display name.",
            "description": "Description or backstory.",
            "location": "Where it appears (required for item/npc, optional for location to set connection).",
            "role": "NPC role/class (e.g., 'guard', 'merchant'). For NPCs only.",
            "goal": "NPC goal/motivation. For NPCs only. Optional.",
        },
        required=["type", "name", "description"],
    ),
    _tool(
        "modify",
        "Change or remove something in the world: update quest status, remove NPC, change location state.",
        {
            "action": {
                "type": "string",
                "enum": ["update_quest", "remove_npc", "update_location"],
                "description": "What modification to make.",
            },
            "target_id": "ID of the quest, NPC, or location to modify.",
            "status": "New status (for quests: active/completed/failed).",
            "reason": "Why this change is happening (for narration/logging).",
        },
        required=["action", "target_id"],
    ),
]


# =============================================================================
# DIRECTOR TOOLS (1)
# =============================================================================

DIRECTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "direct",
            "description": "Select who acts next and provide guidance. Optionally move characters to a new location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "actor": {
                        "type": "string",
                        "description": "Who acts next: character_id or 'dm'.",
                    },
                    "guidance": {
                        "type": "string",
                        "description": "What they should focus on. Frame as internal monologue for characters.",
                    },
                    "move_to": {
                        "type": "string",
                        "description": "Location ID to move characters to (scene transition). Optional.",
                    },
                    "move_characters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Character IDs to move (if move_to is set). Optional.",
                    },
                },
                "required": ["actor", "guidance"],
            },
        },
    },
]


# =============================================================================
# STORYTELLER TOOLS (3)
# =============================================================================

STORYTELLER_TOOLS = [
    _tool(
        "scene",
        "Direct the DM to write a scene. Use for most story beats — the DM writes rich prose, describes action, and speaks for minor NPCs.",
        {
            "dm_guidance": "What should happen in this scene. 2-3 sentences of direction.",
            "dramatic_purpose": {
                "type": "string",
                "enum": ["tension", "revelation", "action", "intimacy", "advancement", "transition"],
                "description": "The emotional/narrative purpose of this scene.",
            },
            "context": "Additional notes for the DM. Optional.",
            "beat_id": "Short identifier for this story beat (e.g., 'ronn_reveals_cellar'). Helps track what's been covered. Optional.",
        },
        required=["dm_guidance", "dramatic_purpose"],
    ),
    _tool(
        "decision_point",
        "Call a character to make a meaningful choice. Use ONLY for real decisions with stakes, not routine actions.",
        {
            "character_id": "Who must decide.",
            "question": "Frame the decision clearly (e.g., 'Does Ronn reveal the truth?').",
            "stakes": "What hangs in the balance.",
            "setup_narration": "Brief DM guidance to set up the moment. Optional.",
        },
        required=["character_id", "question", "stakes"],
    ),
    _tool(
        "transition",
        "Shift between scenes — change location, skip time, or change perspective.",
        {
            "narration": "How to describe the transition.",
            "to_location": "Where we're going. Optional.",
            "characters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Character IDs who move. Optional.",
            },
        },
        required=["narration"],
    ),
]


# =============================================================================
# GETTERS
# =============================================================================


def get_character_tools() -> List[Dict[str, Any]]:
    """Return character tools."""
    return CHARACTER_TOOLS


def get_dm_tools() -> List[Dict[str, Any]]:
    """Return DM tools."""
    return DM_TOOLS


def get_director_tools() -> List[Dict[str, Any]]:
    """Return director tools."""
    return DIRECTOR_TOOLS


def get_storyteller_tools() -> List[Dict[str, Any]]:
    """Return storyteller tools."""
    return STORYTELLER_TOOLS

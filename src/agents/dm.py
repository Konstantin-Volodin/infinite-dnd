"""
DM Agent - Dungeon Master that narrates and controls the world.
"""
from typing import Dict, Any
from .base import BaseAgent
from ..core.models import WorldState
from ..prompts import build_dm_system_prompt, build_dm_context
from ..tools import get_dm_tools


# JSON Schema for structured DM responses
DM_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "action_type": {
            "type": "string",
            "enum": ["narrate", "event", "spawn_npc", "create_location", "create_item"],
            "description": "Type of action to take. Use 'spawn_npc' for new characters, 'create_location' for new places."
        },
        "narration": {
            "type": "string",
            "description": "The narrative text (1-3 sentences, evocative, present tense)"
        },
        "target_location_id": {
            "type": "string",
            "description": "Location ID where this happens (e.g., 'market-square')"
        },
        "spawn_npc": {
            "type": "object",
            "properties": {
                "npc_id": {"type": "string", "description": "Unique ID (lowercase, no spaces)"},
                "name": {"type": "string"},
                "role": {"type": "string", "description": "Class/Role (e.g. 'Bandit Leader')"},
                "description": {"type": "string", "description": "Backstory/Appearance"},
                "goal": {"type": "string", "description": "Immediate goal (e.g. 'Attack the party')"}
            },
            "required": ["npc_id", "name", "role", "description"]
        },
        "create_location": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "connected_from": {"type": "string", "description": "ID of location it connects to"}
            },
            "required": ["name", "description", "connected_from"]
        },
        "new_features": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short name like 'rusted lantern'"},
                    "location_id": {"type": "string"}
                },
                "required": ["name", "location_id"]
            },
            "description": "New things that characters can examine (max 2-3)"
        },
        "new_items": {
            "type": "array", 
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Item name like 'rusted key'"},
                    "location_id": {"type": "string"}
                },
                "required": ["name", "location_id"]
            },
            "description": "New items that can be picked up"
        }
    },
    "required": ["action_type", "narration", "target_location_id"]
}


class DMAgent(BaseAgent):
    """Dungeon Master agent that returns structured JSON responses."""
    
    def decide_action(self, state: WorldState, guidance: str = "") -> Dict[str, Any]:
        """Returns a structured DM response with narration and world updates.
        
        Args:
            guidance: Optional suggestion from the director about what to do.
        """
        context = build_dm_context(state)
        if guidance:
            context = f"{guidance}\n(NOTE: This is a suggestion. As DM, you have final say. Prioritize story coherence and fun.)\n\n{context}"
        
        result = self.llm.chat_json(
            system=build_dm_system_prompt(),
            user=context,
            schema=DM_RESPONSE_SCHEMA
        )
        
        if result["type"] == "json":
            data = result["data"]
            action_type = data.get("action_type", "narrate")
            
            # Handle specific tool calls based on action_type
            if action_type == "spawn_npc" and "spawn_npc" in data:
                npc_data = data["spawn_npc"]
                return {
                    "tool": "spawn_npc",
                    "npc_id": npc_data.get("npc_id"),
                    "name": npc_data.get("name"),
                    "role": npc_data.get("role"),
                    "location_id": data.get("target_location_id"),
                    "description": npc_data.get("description"),
                    "goal": npc_data.get("goal", "")
                }
            
            elif action_type == "create_location" and "create_location" in data:
                loc_data = data["create_location"]
                return {
                    "tool": "create_location",
                    "location_id": loc_data.get("name").lower().replace(" ", "-"),
                    "name": loc_data.get("name"),
                    "description": loc_data.get("description"),
                    "connected_to": [loc_data.get("connected_from")]
                }
                
            elif action_type == "create_item" and "new_items" in data and data["new_items"]:
                # Just take the first item
                item = data["new_items"][0]
                return {
                    "tool": "create_item",
                    "item_name": item.get("name"),
                    "location_id": item.get("location_id") or data.get("target_location_id")
                }
            
            # Default to standard DM action (narrate + features/items)
            return {
                "tool": "dm_action",
                "action_type": action_type,
                "narration": data.get("narration", "..."),
                "target_location_id": data.get("target_location_id"),
                "new_features": data.get("new_features", []),
                "new_items": data.get("new_items", [])
            }
        else:
            print(f"DM JSON error: {result.get('message', 'Unknown')}")
            return {
                "tool": "dm_action",
                "action_type": "narrate",
                "narration": "The scene continues...",
                "target_location_id": None,
                "new_features": [],
                "new_items": []
            }

    def generate_new_location(self, state: WorldState, target_name: str, origin_id: str) -> Dict[str, Any]:
        """Create a new location when a character tries to move somewhere that doesn't exist."""
        origin_loc = state.locations.get(origin_id)
        origin_name = origin_loc.name if origin_loc else origin_id
        
        prompt = f"""A character is trying to move to '{target_name}' from '{origin_name}', but it doesn't exist yet.
Create this location based on its name and the current setting."""

        return self._decide(
            system_prompt=build_dm_system_prompt() + "\n\nYou can use many tools simultaneously and should output all tool calls in 1 response.",
            context=prompt,
            tools=get_dm_tools(),
            fallback_tool="create_location",
            fallback_args={
                "name": target_name, 
                "description": f"A mysterious place known as {target_name}.", 
                "connected_from": origin_id
            }
        )

    def generate_new_item(self, state: WorldState, item_name: str, location_id: str) -> Dict[str, Any]:
        """Validate and create an item when character tries to pick up something not in data."""
        loc = state.locations.get(location_id)
        loc_name = loc.name if loc else location_id
        
        prompt = f"""A character is trying to pick up '{item_name}' at {loc_name}, but it doesn't exist in the world data.
If it makes sense, create it. Otherwise, narrate why they can't take it."""
        
        return self._decide(
            system_prompt=build_dm_system_prompt() + "\n\nYou can use many tools simultaneously and should output all tool calls in 1 response.",
            context=prompt,
            tools=get_dm_tools(),
            fallback_tool="narrate",
            fallback_args={"content": f"You cannot pick up the {item_name}."}
        )

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
                "connected_to": {"type": "array", "items": {"type": "string"}, "description": "IDs of locations it connects to (e.g., origin id)."}
            },
            "required": ["name", "description", "connected_to"]
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
            context = f"{guidance}\n\n{context}"
        
        # Use the tool-calling interface like other agents (narrate, spawn_npc, create_location, etc.)
        # Determine allowed DM tools for current scene type
        scene_type = getattr(state.narrative, 'scene_type', None)
        decision = self._decide(
            system_prompt=build_dm_system_prompt() + "\n\nYou can use many tools simultaneously and should output all tool calls in 1 response.",
            context=context,
            tools=get_dm_tools(scene_type),
            fallback_tool="narrate",
            fallback_args={"content": "The scene continues..."}
        )
        # _decide returns a dict: {'tool': <tool>, ...} or a fallback
        # If the DM used the old JSON schema tools (dm_action), try to convert it to a set of tool calls
        if decision.get("tool") == "dm_action":
            # Convert old-style dm_action into a narrate + optional create/spawn actions
            # Accept both 'narration' and 'narrate' content
            content = decision.get("narration") or decision.get("narration_text") or decision.get("content")
            target_loc = decision.get("target_location_id")
            # Emit narrate as first tool
            calls = [{"tool": "narrate", "content": content}] if content else []
            # New features/items are expressed in dm_action as 'new_features'/'new_items' arrays; convert to create_item calls
            for f in decision.get("new_items", []) or []:
                if isinstance(f, dict):
                    calls.append({"tool": "create_item", "item_name": f.get("name"), "location_id": f.get("location_id") or target_loc})
                else:
                    calls.append({"tool": "create_item", "item_name": f, "location_id": target_loc})
            # spawn_npc not part of this path; but if dm_action included spawn_npc, convert
            if decision.get("spawn_npc"):
                sp = decision.get("spawn_npc")
                calls.append({"tool": "spawn_npc", "npc_id": sp.get("npc_id"), "name": sp.get("name"), "role": sp.get("role"), "description": sp.get("description"), "location_id": sp.get("location_id") or target_loc, "goal": sp.get("goal", "")})
            # Return first call along with all_calls for the runner to execute sequentially
            if calls:
                first = calls[0].copy()
                first["all_calls"] = [{"tool": c["tool"], "arguments": {k: v for k, v in c.items() if k != "tool"}} for c in calls]
                return first
            else:
                return {"tool": "narrate", "content": "The scene continues..."}
        # Normalize some args for compatibility
        if decision.get("tool") == "create_location":
            ct = decision.get("connected_to")
            if isinstance(ct, str):
                decision["connected_to"] = [ct]
        # Enforce allowed tools for the current scene type (safety check):
        allowed_tools = {t["function"]["name"] for t in get_dm_tools(scene_type)}
        # If the DM returned multiple calls, filter them; otherwise, enforce single tool
        if "all_calls" in decision:
            filtered_calls = [c for c in decision["all_calls"] if c["tool"] in allowed_tools]
            if not filtered_calls:
                # Nothing allowed - fallback to narrator
                return {"tool": "narrate", "content": "The scene continues..."}
            # Keep first call as primary, and update all_calls
            first = filtered_calls[0].copy()
            first["all_calls"] = [{"tool": c["tool"], "arguments": c.get("arguments", {})} for c in filtered_calls]
            return first
        else:
            if decision.get("tool") not in allowed_tools:
                # Not allowed - convert to narrate for safety
                return {"tool": "narrate", "content": decision.get("content") or "The scene continues..."}
        return decision

    def generate_new_location(self, state: WorldState, target_name: str, origin_id: str) -> Dict[str, Any]:
        """Create a new location when a character tries to move somewhere that doesn't exist."""
        origin_loc = state.locations.get(origin_id)
        origin_name = origin_loc.name if origin_loc else origin_id
        
        prompt = f"""A character is trying to move to '{target_name}' from '{origin_name}', but it doesn't exist yet.
Create this location based on its name and the current setting."""

        return self._decide(
            system_prompt=build_dm_system_prompt() + "\n\nYou can use many tools simultaneously and should output all tool calls in 1 response.",
            context=prompt,
            tools=get_dm_tools(state.narrative.scene_type),
            fallback_tool="create_location",
            fallback_args={
                "name": target_name, 
                "description": f"A mysterious place known as {target_name}.", 
                "connected_to": [origin_id]
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
            tools=get_dm_tools(state.narrative.scene_type),
            fallback_tool="narrate",
            fallback_args={"content": f"You cannot pick up the {item_name}."}
        )

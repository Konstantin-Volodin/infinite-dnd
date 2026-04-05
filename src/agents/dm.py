"""
DM Agent - Dungeon Master that narrates and controls the world.
"""
from __future__ import annotations

from typing import Dict, Any
from .base import BaseAgent
from ..core.models import WorldState
from ..prompts import build_dm_system_prompt, build_dm_context
from ..tools import DM_TOOLS


class DMAgent(BaseAgent):
    """Dungeon Master agent that narrates and creates world content."""

    def react(
        self, state: WorldState, last_action: Dict[str, Any] | None = None, tool_executor=None
    ) -> Dict[str, Any]:
        """React to the latest character action using DM tools."""
        context = build_dm_context(state, last_action=last_action)

        return self._decide(
            system_prompt=build_dm_system_prompt()
            + "\n\nYou can take multiple actions per turn. After each action you see the result and decide what to do next. When done, stop calling tools.",
            context=context,
            tools=DM_TOOLS,
            fallback_tool="narrate",
            fallback_args={"content": "The scene continues..."},
            tool_executor=tool_executor,
        )

    def generate_new_location(
        self, state: WorldState, target_name: str, origin_id: str
    ) -> Dict[str, Any]:
        """Create a new location when a character tries to move somewhere that doesn't exist."""
        origin_loc = state.locations.get(origin_id)
        origin_name = origin_loc.id if origin_loc else origin_id

        prompt = f"""A character is trying to move to '{target_name}' from '{origin_name}', but it doesn't exist yet.
Create this location using the `create` tool with type="location"."""

        return self._decide(
            system_prompt=build_dm_system_prompt(),
            context=prompt,
            tools=DM_TOOLS,
            fallback_tool="create",
            fallback_args={
                "type": "location",
                "name": target_name,
                "description": f"A place known as {target_name}.",
                "location": origin_id,
            },
        )

    def generate_new_item(
        self, state: WorldState, item_name: str, location: str
    ) -> Dict[str, Any]:
        """Validate and create an item when character tries to pick up something not in data."""
        loc = state.locations.get(location)
        loc_name = loc.id if loc else location

        prompt = f"""A character is trying to pick up '{item_name}' at {loc_name}, but it doesn't exist in the world data.
If it makes sense, create it using `create` with type="item". Otherwise, narrate why they can't take it."""

        return self._decide(
            system_prompt=build_dm_system_prompt(),
            context=prompt,
            tools=DM_TOOLS,
            fallback_tool="narrate",
            fallback_args={"content": f"You cannot pick up the {item_name}."},
        )

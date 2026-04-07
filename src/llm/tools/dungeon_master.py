# src/llm/tools/dungeon_master.py
"""dungeon master tools logic - defines how world actions affect the world state."""

from src.core.models import WorldState
from src.core.state import add_history
from src.llm.tools.world import create_item, discover_location, spawn_npc
from src.llm.tools.world import default_anchor_location, narrate as world_narrate
from src.llm.tools.world import resolve_location_id, update_quest_status


def narrate(state: WorldState, content: str, location: str = "") -> str:
    return world_narrate(state, content, location=location)


def create(
    state: WorldState,
    type: str,
    name: str,
    description: str,
    id: str | None = None,
    location: str | None = None,
    role: str | None = None,
    goal: str | None = None,
) -> str:
    kind = (type or "").strip().lower()
    if kind == "location":
        return discover_location(state, name=name, description=description, location_id=id, anchor_location=location)
    if kind == "item":
        return create_item(state, item_name=name, description=description, location=location)
    if kind == "npc":
        return spawn_npc(
            state,
            name=name,
            description=description,
            role=role,
            location=location,
            goal=goal,
            npc_id=id,
        )
    return f"Unknown create type: {type!r}."


def _remove_npc(state: WorldState, target_id: str, reason: str | None = None) -> str:
    char = state.characters.get(target_id)
    if not char:
        return f"Cannot remove NPC {target_id!r} - character not found."

    location = char.location if char.location in state.locations else default_anchor_location(state)
    message = f"{char.id} {reason or 'leaves the scene.'}"
    if not message.endswith("."):
        message += "."

    del state.characters[target_id]
    add_history(state, message, location)
    return f"Removed NPC {target_id}."


def _update_location(state: WorldState, target_id: str, reason: str | None = None) -> str:
    location_id = resolve_location_id(state, target_id)
    loc = state.locations.get(location_id or "")
    if not loc:
        return f"Cannot update location {target_id!r} - location not found."

    if reason:
        add_history(state, f"{loc.id}: {reason}", loc.id)
        return f"Updated location {loc.id}."
    return f"Location {loc.id} is unchanged."


def modify(
    state: WorldState,
    action: str,
    target_id: str,
    status: str | None = None,
    reason: str | None = None,
) -> str:
    kind = (action or "").strip().lower()
    if kind == "update_quest":
        if not status:
            return "Cannot update a quest without a status."
        return update_quest_status(state, target_id=target_id, status=status)
    if kind == "remove_npc":
        return _remove_npc(state, target_id=target_id, reason=reason)
    if kind == "update_location":
        return _update_location(state, target_id=target_id, reason=reason)
    return f"Unknown modify action: {action!r}."

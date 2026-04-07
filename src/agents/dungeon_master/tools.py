# src/llm/tools/dungeon_master.py
"""dungeon master tools logic - defines how world actions affect the world state."""

from src.engine.models import WorldState
from src.engine.world import create_item, discover_location, narrate as world_narrate
from src.engine.world import remove_npc, spawn_npc, update_location, update_quest_status


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
        return remove_npc(state, target_id=target_id, reason=reason)
    if kind == "update_location":
        return update_location(state, target_id=target_id, reason=reason)
    return f"Unknown modify action: {action!r}."

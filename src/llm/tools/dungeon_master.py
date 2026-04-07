# src/llm/tools/dungeon_master.py
"""dungeon master tools logic - defines how world actions affect the world state."""

from src.core.models import Character, CharacterStats, Location, Quest, WorldState
from src.core.state import add_history
from src.core.utils import slugify


def _resolve_location_id(state: WorldState, raw_location: str | None) -> str | None:
    if not raw_location:
        return raw_location
    if raw_location in state.locations:
        return raw_location

    normalized = slugify(raw_location)
    if normalized in state.locations:
        return normalized
    return raw_location


def _default_anchor_location(state: WorldState) -> str:
    first_char = next(iter(state.characters.values()), None)
    if first_char and first_char.location in state.locations:
        return first_char.location
    first_location = next(iter(state.locations.keys()), "")
    return first_location


def _quest_event_location(state: WorldState, quest: Quest) -> str:
    owner = state.characters.get(quest.owner)
    if owner and owner.location in state.locations:
        return owner.location
    return _default_anchor_location(state)


def narrate(state: WorldState, content: str, location: str = "") -> str:
    narration = (content or "").strip()
    if not narration:
        return "Cannot narrate an empty event."

    history_location = _resolve_location_id(state, location) or _default_anchor_location(state)
    add_history(state, narration, history_location)
    return narration


def _create_location(
    state: WorldState,
    name: str,
    description: str,
    location_id: str | None = None,
    anchor_location: str | None = None,
) -> str:
    resolved_id = slugify(location_id or name)
    if not resolved_id:
        return "Cannot create a location without a valid name."
    if resolved_id in state.locations:
        return f"Cannot create location {resolved_id!r} - it already exists."

    anchor_id = _resolve_location_id(state, anchor_location) or _default_anchor_location(state)
    connections: list[str] = []
    if anchor_id and anchor_id in state.locations and anchor_id != resolved_id:
        connections.append(anchor_id)

    state.locations[resolved_id] = Location(
        id=resolved_id,
        name=name,
        description=description,
        connections=connections,
    )

    for connection_id in connections:
        other = state.locations.get(connection_id)
        if other and resolved_id not in other.connections:
            other.connections.append(resolved_id)

    if anchor_id:
        add_history(state, f"A new place becomes known: {resolved_id}.", anchor_id)
    return f"Created location {resolved_id}."


def _create_item(state: WorldState, item_name: str, location: str | None) -> str:
    location_id = _resolve_location_id(state, location) or _default_anchor_location(state)
    loc = state.locations.get(location_id)
    if not loc:
        return f"Cannot create item {item_name!r} - location {location!r} was not found."
    if item_name in loc.items:
        return f"Cannot create item {item_name!r} - it already exists at {loc.id}."

    loc.items.append(item_name)
    add_history(state, f"{item_name} is now available at {loc.id}.", loc.id)
    return f"Created item {item_name} at {loc.id}."


def _spawn_npc(
    state: WorldState,
    name: str,
    role: str | None,
    location: str | None,
    description: str,
    goal: str | None,
    npc_id: str | None = None,
) -> str:
    resolved_id = slugify(npc_id or name)
    if not resolved_id:
        return "Cannot create an NPC without a valid name."
    if resolved_id in state.characters:
        return f"Cannot create NPC {resolved_id!r} - they already exist."

    location_id = _resolve_location_id(state, location) or _default_anchor_location(state)
    loc = state.locations.get(location_id)
    if not loc:
        return f"Cannot create NPC {resolved_id!r} - location {location!r} was not found."

    state.characters[resolved_id] = Character(
        id=resolved_id,
        role=role or "commoner",
        backstory=description,
        goal=goal or "",
        location=loc.id,
        stats=CharacterStats(hp=15, max_hp=15),
    )
    add_history(state, f"{resolved_id} arrives at {loc.id}.", loc.id)
    return f"Created NPC {resolved_id} at {loc.id}."


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
        return _create_location(state, name=name, description=description, location_id=id, anchor_location=location)
    if kind == "item":
        return _create_item(state, item_name=name, location=location)
    if kind == "npc":
        return _spawn_npc(
            state,
            name=name,
            role=role,
            location=location,
            description=description,
            goal=goal,
            npc_id=id,
        )
    return f"Unknown create type: {type!r}."


def _update_quest(state: WorldState, target_id: str, status: str) -> str:
    quest = state.quests.get(target_id)
    if not quest:
        target_slug = slugify(target_id)
        quest = next(
            (
                candidate
                for candidate in state.quests.values()
                if slugify(candidate.id) == target_slug or slugify(candidate.title) == target_slug
            ),
            None,
        )
    if not quest:
        return f"Cannot update quest {target_id!r} - quest not found."

    old_status = quest.status
    quest.status = status
    add_history(
        state,
        f"Quest '{quest.title}' changed from {old_status} to {status}.",
        _quest_event_location(state, quest),
    )
    return f"Updated quest {quest.id} to {status}."


def _remove_npc(state: WorldState, target_id: str, reason: str | None = None) -> str:
    char = state.characters.get(target_id)
    if not char:
        return f"Cannot remove NPC {target_id!r} - character not found."

    location = char.location if char.location in state.locations else _default_anchor_location(state)
    message = f"{char.id} {reason or 'leaves the scene.'}"
    if not message.endswith("."):
        message += "."

    del state.characters[target_id]
    add_history(state, message, location)
    return f"Removed NPC {target_id}."


def _update_location(state: WorldState, target_id: str, reason: str | None = None) -> str:
    location_id = _resolve_location_id(state, target_id)
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
        return _update_quest(state, target_id=target_id, status=status)
    if kind == "remove_npc":
        return _remove_npc(state, target_id=target_id, reason=reason)
    if kind == "update_location":
        return _update_location(state, target_id=target_id, reason=reason)
    return f"Unknown modify action: {action!r}."

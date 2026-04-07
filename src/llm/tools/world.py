"""Shared world-mutation helpers for agent tools."""

from src.engine.models import Character, CharacterStats, Location, Quest, WorldState
from src.engine.state import add_history
from src.engine.utils import slugify


def _resolve_named_value(values: list[str], raw_value: str) -> str | None:
    target = slugify(raw_value)
    for value in values:
        if slugify(value) == target:
            return value
    return None


def resolve_character(state: WorldState, raw_character_id: str | None) -> Character | None:
    if not raw_character_id:
        return None
    if raw_character_id in state.characters:
        return state.characters[raw_character_id]

    normalized = slugify(raw_character_id)
    for char in state.characters.values():
        if slugify(char.id) == normalized:
            return char
    return None


def characters_in_location(
    state: WorldState,
    location_id: str,
    *,
    exclude_character_id: str | None = None,
) -> list[Character]:
    return [
        char
        for char in state.characters.values()
        if char.location == location_id and char.id != exclude_character_id
    ]


def resolve_location_id(state: WorldState, raw_location: str | None) -> str | None:
    if not raw_location:
        return raw_location
    if raw_location in state.locations:
        return raw_location

    normalized = slugify(raw_location)
    if normalized in state.locations:
        return normalized
    return raw_location


def default_anchor_location(state: WorldState) -> str:
    first_char = next(iter(state.characters.values()), None)
    if first_char and first_char.location in state.locations:
        return first_char.location
    first_location = next(iter(state.locations.keys()), "")
    return first_location


def connected_location_ids(state: WorldState, location_id: str) -> list[str]:
    loc = state.locations.get(location_id)
    if not loc:
        return []
    return [connection_id for connection_id in loc.connections if connection_id in state.locations]


def resolve_quest(state: WorldState, target_id: str) -> Quest | None:
    quest = state.quests.get(target_id)
    if quest:
        return quest

    target_slug = slugify(target_id)
    return next(
        (
            candidate
            for candidate in state.quests.values()
            if slugify(candidate.id) == target_slug or slugify(candidate.title) == target_slug
        ),
        None,
    )


def _quest_event_location(state: WorldState, quest: Quest) -> str:
    owner = state.characters.get(quest.owner)
    if owner and owner.location in state.locations:
        return owner.location
    return default_anchor_location(state)


def narrate(state: WorldState, content: str, location: str = "") -> str:
    narration = (content or "").strip()
    if not narration:
        return "Cannot narrate an empty event."

    history_location = resolve_location_id(state, location) or default_anchor_location(state)
    add_history(state, narration, history_location)
    return narration


def discover_location(
    state: WorldState,
    name: str,
    description: str,
    *,
    location_id: str | None = None,
    anchor_location: str | None = None,
) -> str:
    resolved_id = slugify(location_id or name)
    if not resolved_id:
        return "Cannot create a location without a valid name."

    anchor_id = resolve_location_id(state, anchor_location) or default_anchor_location(state)
    if anchor_id and anchor_id not in state.locations:
        return f"Cannot connect {resolved_id!r} - anchor location {anchor_location!r} was not found."

    existing = state.locations.get(resolved_id)
    if existing:
        if anchor_id and anchor_id != resolved_id and anchor_id not in existing.connections:
            existing.connections.append(anchor_id)
            anchor = state.locations.get(anchor_id)
            if anchor and resolved_id not in anchor.connections:
                anchor.connections.append(resolved_id)
        return f"Location {resolved_id} is already known."

    connections: list[str] = []
    if anchor_id and anchor_id != resolved_id:
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


def remember(state: WorldState, character_id: str, knowledge: str) -> str:
    char = resolve_character(state, character_id)
    if not char:
        return f"Cannot add knowledge to {character_id!r} - character not found."

    learned = (knowledge or "").strip()
    if not learned:
        return "Cannot add an empty piece of knowledge."
    if learned in char.knowledge:
        return f"{char.id} already knows that."

    char.knowledge.append(learned)
    add_history(state, f"{char.id} learns: {learned}", char.location)
    return f"Added knowledge for {char.id}."


def add_location_feature(state: WorldState, detail: str, location: str | None = None) -> str:
    feature = (detail or "").strip()
    if not feature:
        return "Cannot add an empty location detail."

    location_id = resolve_location_id(state, location) or default_anchor_location(state)
    loc = state.locations.get(location_id)
    if not loc:
        return f"Cannot update location {location!r} - location not found."
    if feature in loc.features:
        return f"Feature already known at {loc.id}."

    loc.features.append(feature)
    add_history(state, f"{loc.id}: {feature}", loc.id)
    return f"Added a new feature to {loc.id}."


def adjust_hit_points(state: WorldState, character_id: str, delta: int, reason: str | None = None) -> str:
    char = resolve_character(state, character_id)
    if not char:
        return f"Cannot change HP for {character_id!r} - character not found."

    old_hp = char.stats.hp
    new_hp = max(0, min(char.stats.max_hp, old_hp + delta))
    actual_delta = new_hp - old_hp
    if actual_delta == 0:
        return f"{char.id}'s HP is unchanged."

    char.stats.hp = new_hp
    direction = "gains" if actual_delta > 0 else "loses"
    amount = abs(actual_delta)
    message = f"{char.id} {direction} {amount} HP"
    if reason:
        message += f" ({reason.strip()})"
    message += "."
    add_history(state, message, char.location)
    return f"Updated HP for {char.id} to {char.stats.hp}/{char.stats.max_hp}."


def update_quest_status(state: WorldState, target_id: str, status: str) -> str:
    quest = resolve_quest(state, target_id)
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


def take_item(state: WorldState, character_id: str, item_name: str, location: str | None = None) -> str:
    char = resolve_character(state, character_id)
    if not char:
        return f"Cannot take item as {character_id!r} - character not found."

    location_id = resolve_location_id(state, location) or char.location
    loc = state.locations.get(location_id)
    if not loc:
        return f"Cannot take item from {location!r} - location not found."

    resolved_item = _resolve_named_value(loc.items, item_name)
    if not resolved_item:
        return f"Cannot take item {item_name!r} - item not found at {loc.id}."
    if resolved_item in char.inventory:
        return f"{char.id} already has {resolved_item}."

    loc.items.remove(resolved_item)
    char.inventory.append(resolved_item)
    add_history(state, f"{char.id} takes {resolved_item} from {loc.id}.", loc.id)
    return f"{char.id} takes {resolved_item}."


def drop_item(state: WorldState, character_id: str, item_name: str, location: str | None = None) -> str:
    char = resolve_character(state, character_id)
    if not char:
        return f"Cannot drop item as {character_id!r} - character not found."

    location_id = resolve_location_id(state, location) or char.location
    loc = state.locations.get(location_id)
    if not loc:
        return f"Cannot drop item at {location!r} - location not found."

    resolved_item = _resolve_named_value(char.inventory, item_name)
    if not resolved_item:
        return f"Cannot drop item {item_name!r} - item not carried by {char.id}."
    if resolved_item in loc.items:
        return f"{resolved_item} is already at {loc.id}."

    char.inventory.remove(resolved_item)
    loc.items.append(resolved_item)
    add_history(state, f"{char.id} leaves {resolved_item} at {loc.id}.", loc.id)
    return f"{char.id} drops {resolved_item}."


def create_item(state: WorldState, item_name: str, description: str | None = None, location: str | None = None) -> str:
    location_id = resolve_location_id(state, location) or default_anchor_location(state)
    loc = state.locations.get(location_id)
    if not loc:
        return f"Cannot create item {item_name!r} - location {location!r} was not found."
    if item_name in loc.items:
        return f"Cannot create item {item_name!r} - it already exists at {loc.id}."

    label = f"{item_name}: {description}" if description else item_name
    loc.items.append(label)
    add_history(state, f"{label} is now available at {loc.id}.", loc.id)
    return f"Created item {item_name} at {loc.id}."


def spawn_npc(
    state: WorldState,
    name: str,
    description: str,
    role: str | None = None,
    location: str | None = None,
    goal: str | None = None,
    npc_id: str | None = None,
) -> str:
    resolved_id = slugify(npc_id or name)
    if not resolved_id:
        return "Cannot create an NPC without a valid name."
    if resolved_id in state.characters:
        return f"Cannot create NPC {resolved_id!r} - they already exist."

    location_id = resolve_location_id(state, location) or default_anchor_location(state)
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
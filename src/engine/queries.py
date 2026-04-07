"""Read-only helpers for world state lookups."""

from src.engine.models import Character, Quest, WorldState
from src.engine.utils import slugify


def resolve_character(state: WorldState, raw_character_id: str | None) -> Character | None:
    if not raw_character_id:
        return None
    if raw_character_id in state.characters:
        return state.characters[raw_character_id]

    normalized = slugify(raw_character_id)
    for character in state.characters.values():
        if slugify(character.id) == normalized:
            return character
    for character in state.characters.values():
        if normalized and normalized in slugify(character.id):
            return character
    return None


def characters_in_location(
    state: WorldState,
    location_id: str,
    *,
    exclude_character_id: str | None = None,
) -> list[Character]:
    return [
        character
        for character in state.characters.values()
        if character.location == location_id and character.id != exclude_character_id
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
    first_character = next(iter(state.characters.values()), None)
    if first_character and first_character.location in state.locations:
        return first_character.location
    return next(iter(state.locations.keys()), "")


def connected_location_ids(state: WorldState, location_id: str) -> list[str]:
    location = state.locations.get(location_id)
    if not location:
        return []
    return [connection_id for connection_id in location.connections if connection_id in state.locations]


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
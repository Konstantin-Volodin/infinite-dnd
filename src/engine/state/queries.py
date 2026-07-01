"""Read-only lookups over WorldState. Fuzzy id resolution lives here."""

import re

from src.engine.state.models import Character, WorldState


def slugify(text: str) -> str:
    text = text.strip().lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9\- ]+", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def resolve_character(state: WorldState, raw: str | None) -> Character | None:
    if not raw:
        return None
    if raw in state.characters:
        return state.characters[raw]

    needle = slugify(raw)
    for char in state.characters.values():
        if slugify(char.id) == needle:
            return char
    for char in state.characters.values():
        if needle and needle in slugify(char.id):
            return char
    return None


def resolve_location_id(state: WorldState, raw: str | None) -> str | None:
    if not raw:
        return None
    if raw in state.locations:
        return raw

    needle = slugify(raw)
    for loc_id in state.locations:
        if slugify(loc_id) == needle:
            return loc_id
    for loc_id in state.locations:
        if needle and needle in slugify(loc_id):
            return loc_id
    return None


def characters_in_location(
    state: WorldState, location_id: str, *, exclude_character_id: str | None = None
) -> list[Character]:
    return [
        c for c in state.characters.values()
        if c.location == location_id and c.id != exclude_character_id
    ]


def connected_location_ids(state: WorldState, location_id: str) -> list[str]:
    loc = state.locations.get(location_id)
    if not loc:
        return []
    return [c for c in loc.connections if c in state.locations]

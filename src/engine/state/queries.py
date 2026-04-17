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


if __name__ == "__main__":
    import logging
    from src.engine.state.models import Character, Location, WorldState

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # slugify
    assert slugify("Hidden Cellar") == "hidden-cellar"
    assert slugify("  The_Ancient  Library  ") == "the-ancient-library"
    assert slugify("Elara Swift!") == "elara-swift"
    assert slugify("") == ""
    logging.info("slugify tests passed.")

    state = WorldState(
        locations={
            "tavern": Location(id="tavern", connections=["forest"]),
            "forest": Location(id="forest", connections=["tavern", "missing"]),
        },
        characters={
            "elara-swift": Character(id="elara-swift", role="ranger", location="forest"),
            "bram-the-bold": Character(id="bram-the-bold", role="fighter", location="tavern"),
        },
    )

    # resolve_character: exact, slug, substring, miss
    assert resolve_character(state, "elara-swift").id == "elara-swift"
    assert resolve_character(state, "Elara Swift").id == "elara-swift"
    assert resolve_character(state, "bram").id == "bram-the-bold"
    assert resolve_character(state, None) is None
    assert resolve_character(state, "ghost") is None
    logging.info("resolve_character tests passed.")

    # resolve_location_id: exact, slug, substring, miss
    assert resolve_location_id(state, "tavern") == "tavern"
    assert resolve_location_id(state, "Tavern") == "tavern"
    assert resolve_location_id(state, "for") == "forest"
    assert resolve_location_id(state, None) is None
    assert resolve_location_id(state, "void") is None
    logging.info("resolve_location_id tests passed.")

    # characters_in_location
    assert [c.id for c in characters_in_location(state, "tavern")] == ["bram-the-bold"]
    assert characters_in_location(state, "tavern", exclude_character_id="bram-the-bold") == []
    assert characters_in_location(state, "nowhere") == []
    logging.info("characters_in_location tests passed.")

    # connected_location_ids — drops connections that point to missing locations
    assert connected_location_ids(state, "tavern") == ["forest"]
    assert connected_location_ids(state, "forest") == ["tavern"]
    assert connected_location_ids(state, "nowhere") == []
    logging.info("connected_location_ids tests passed.")

    logging.info(f"{__file__} tests completed successfully.")

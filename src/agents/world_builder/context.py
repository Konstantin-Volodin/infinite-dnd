"""World builder prompt builders."""

from src.engine.state import WorldState
from src.agents.utils import render


def world_builder_system() -> str:
    return render("world_builder/identity.jinja")


def world_builder_context(state: WorldState, window: int = 8) -> str:
    events = [e.text for e in state.history[-window:]]
    location_ids = sorted(state.locations.keys())
    character_ids = sorted(state.characters.keys())
    item_ids = sorted(
        {item for loc in state.locations.values() for item in loc.items}
        | {item for char in state.characters.values() for item in char.inventory}
    )
    quest_ids = sorted(state.quests.keys())
    return render(
        "world_builder/state.jinja",
        events=events,
        location_ids=location_ids,
        character_ids=character_ids,
        item_ids=item_ids,
        quest_ids=quest_ids,
    )

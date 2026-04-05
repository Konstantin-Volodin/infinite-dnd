"""Director prompt builders — system prompt and context."""
from __future__ import annotations

from src.core.models import WorldState
from src.prompts.loader import render


def build_director_system_prompt() -> str:
    """Build the director's system prompt."""
    return render("director/system.jinja")


def build_director_context(state: WorldState, location_id: str | None = None) -> str:
    """Build context for selecting and acting as one character."""
    scope_label = "all locations"
    scoped_chars = list(state.characters.values())

    if location_id and location_id in state.locations:
        scope_label = location_id
        scoped_chars = [c for c in state.characters.values() if c.location == location_id]

    if not scoped_chars:
        scoped_chars = list(state.characters.values())
        scope_label = "all locations"

    candidates = []
    for c in scoped_chars:
        loc = state.locations.get(c.location)
        candidates.append({
            "id": c.id,
            "loc_name": loc.id if loc else c.location,
            "goal": c.goal,
            "personality": c.personality,
            "recent_knowledge": c.knowledge[-3:] if c.knowledge else [],
        })

    events = [e.text for e in state.history[-8:]]

    return render(
        "director/context.jinja",
        scope_label=scope_label,
        candidates=candidates,
        events=events,
    )

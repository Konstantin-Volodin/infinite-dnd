#src/prompts/character/build.py

"""Character prompt builders — system prompt and context."""
from __future__ import annotations
from src.core.models import WorldState, Character
from src.prompts.loader import render
from src.core.rules import get_health_status


def build_character_system_prompt(char: Character) -> str:
    """build the character identity."""
    return render("character/system.jinja", char=char)


def build_character_context(char: Character, state: WorldState) -> str:
    """build the character context."""

    # internal status
    health_status = get_health_status(char)
    loc = state.locations.get(char.location)
    knowledge = char.knowledge[-5:] if char.knowledge else []

    # relevant quests
    quests = []
    for q in state.quests.values():
        if str(getattr(q, "status", "active")).lower() in ("completed", "failed"): continue
        if q.owner == char.id: quests.append(q)

    # Recent events (only ones this character witnessed)
    recent_events = [
        e.text for e in state.history
        if char.id in e.characters
    ][-20:]

    # Someone speaking to me?
    someone_speaking_to_me = False
    if recent_events:
        last = recent_events[-1]
        is_dialogue = '"' in last or "says" in last.lower()
        is_someone_else = not last.startswith(char.id)
        someone_speaking_to_me = is_dialogue and is_someone_else

    # Others present
    others = [
        f"{c.id} ({c.role or c.type.value})"
        for c in state.characters.values()
        if c.location == char.location and c.id != char.id
    ]

    # Warnings
    warnings: list[str] = []
    if recent_events and recent_events[-1].startswith(f"{char.id}"):
        warnings.append("*I just acted. I should wait to see what happens.*")
    if sum(1 for e in recent_events[-5:] if '"' in e or "says" in e.lower()) >= 4:
        warnings.append("*Lots of talking. Maybe time for action.*")

    return render(
        "character/context.jinja",
        char=char,
        health_status=health_status,
        loc=loc,
        knowledge=knowledge,
        recent_events=recent_events,
        someone_speaking_to_me=someone_speaking_to_me,
        others=others,
        quests=quests,
        warnings=warnings,
    )

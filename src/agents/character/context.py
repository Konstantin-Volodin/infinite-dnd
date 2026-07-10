"""Character prompt builders - system prompt and context."""

from src.engine.state import Character, WorldState, characters_in_location
from src.engine.rules import get_health_status
from src.agents.utils import render


def character_system(char: Character) -> str:
    """Build the character identity."""
    return render("character/identity.jinja", char=char)


def character_context(char: Character, state: WorldState) -> str:
    """Build the character context."""

    # internal status
    health_status = get_health_status(char)
    loc = state.locations.get(char.location)
    knowledge = char.knowledge[-5:] if char.knowledge else []

    # relevant quests
    quests = []
    for q in state.quests.values():
        if str(getattr(q, "status", "active")).lower() in ("completed", "failed"): continue
        if q.owner == char.id: quests.append(q)
    quest_ids = {quest.id for quest in quests}
    deadlines = [
        (faction.name, clock)
        for faction in (state.factions[fid] for fid in sorted(state.factions))
        for clock in sorted(faction.clocks, key=lambda candidate: candidate.id)
        if clock.fail_quest_id in quest_ids and not clock.consequence_triggered
    ]

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

    # Others present, with visible condition (role, health if not healthy)
    present_characters = characters_in_location(state, char.location, exclude_character_id=char.id)
    others = []
    for c in present_characters:
        status = get_health_status(c)
        tags = [t for t in (c.role, status if status != "healthy" else "") if t]
        if disposition := c.relationships.get(char.id):
            tags.append(f"thinks of me: {disposition}")
        others.append(f"{c.id} ({', '.join(tags)})" if tags else c.id)
    speak_targets = [c.id for c in present_characters if c.stats.hp > 0]
    # Warnings
    warnings: list[str] = []
    if sum(1 for e in recent_events[-5:] if '"' in e or "says" in e.lower()) >= 4:
        warnings.append("*Lots of talking. Maybe time for action.*")

    return render(
        "character/state.jinja",
        char=char,
        health_status=health_status,
        loc=loc,
        knowledge=knowledge,
        chronicle=state.chronicle[-3:],
        recent_events=recent_events,
        someone_speaking_to_me=someone_speaking_to_me,
        others=others,
        speak_targets=speak_targets,
        quests=quests,
        deadlines=deadlines,
        warnings=warnings,
    )

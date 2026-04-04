"""Character context builders — what the character sees each turn."""
from __future__ import annotations

from src.core.models import WorldState, Character


def build_character_context(char: Character, state: WorldState) -> str:
    """Build the Character's context in first-person."""
    loc = state.locations.get(char.location)
    if not loc:
        return "I'm somewhere unfamiliar..."

    sections = []

    # --- Section 1: What Just Happened ---
    lines = ["## 💭 What Just Happened", ""]
    recent = state.history[-10:] if state.history else []
    if recent:
        for i, event in enumerate(recent):
            if i == len(recent) - 1:
                lines.append(f"*Just now:* {event}")
            else:
                lines.append(f"- {event}")

        # Check if someone is talking to me
        last_event = state.history[-1].lower()
        char_mentioned = char.id.lower() in last_event
        has_dialogue = (
            '"' in state.history[-1] or "says" in last_event or "asks" in last_event
        )
        if char_mentioned and has_dialogue:
            lines.append("")
            lines.append("> **Someone just spoke to me.** I should respond.")
    else:
        lines.append("_Everything is calm... for now._")
    sections.append("\n".join(lines))

    # --- Section 2: Where I Am ---
    lines = ["## 🏠 Where I Am", ""]
    lines.append(f"**{loc.id}**")
    lines.append(f"_{loc.description}_")
    lines.append("")

    # Others present
    others = [
        f"{c.id} ({c.role or c.type.value})"
        for c in state.characters.values()
        if c.location == char.location and c.id != char.id
    ]
    if others:
        lines.append(f"**Who's Here:** {', '.join(others)}")
    else:
        lines.append("**I'm alone here.**")

    # Interactables
    examine_targets = []
    if loc.features:
        lines.append(f"**Features:** {', '.join(loc.features)}")
        examine_targets.extend(loc.features)
    if loc.items:
        lines.append(f"**Items:** {', '.join(loc.items)}")
        examine_targets.extend(loc.items)
    if loc.connections:
        lines.append(f"**Exits:** {', '.join(loc.connections)}")

    if examine_targets:
        lines.append("")
        lines.append(f"**[INTERACTABLES]** {', '.join(examine_targets)}")
    sections.append("\n".join(lines))

    # --- Section 3: My Condition ---
    lines = ["## ❤️ My Condition", ""]
    try:
        from src.core.rules import get_health_status

        status = get_health_status(char)
    except Exception:
        status = "unknown"

    hp = char.stats.hp if char.stats else "?"
    max_hp = char.stats.max_hp if char.stats else "?"
    inventory = ", ".join(char.inventory) if char.inventory else "nothing"

    lines.append(f"**Health:** {hp}/{max_hp} HP ({status})")
    lines.append(f"**Carrying:** {inventory}")
    sections.append("\n".join(lines))

    # --- Section 4: What Drives Me ---
    lines = ["## 🎯 What Drives Me", ""]
    if char.goal:
        lines.append(f"**My Goal:** {char.goal}")
    if len(lines) > 2:
        sections.append("\n".join(lines))

    # --- Section 5: What I Know (Knowledge & Leads) ---
    lines = ["## 🧠 What I Know", ""]
    if getattr(char, "knowledge", None) and char.knowledge:
        lines.append("**Leads & Information:**")
        for k in char.knowledge[-5:]:
            lines.append(f"- {k}")
    if len(lines) > 2:
        sections.append("\n".join(lines))

    # --- Section 6: My Quests (only quests I know about) ---
    my_quests = []
    for q in state.quests.values():
        if str(getattr(q, "status", "active")).lower() in ("completed", "failed"):
            continue
        # Quest assigned to me?
        if q.owner == char.id:
            my_quests.append(q)
        # Quest mentioned in my knowledge?
        elif any(q.title.lower() in k.lower() or q.id.lower() in k.lower() for k in char.knowledge):
            my_quests.append(q)
        # Quest is about me (my name in title/description)?
        elif char.id.lower() in q.title.lower() or char.id.lower() in q.description.lower():
            my_quests.append(q)
    if my_quests:
        lines = ["## 📜 My Quests", ""]
        for q in my_quests:
            lines.append(f"**{q.title}**")
            lines.append(f"_{q.description}_")
            if q.steps:
                lines.append(f"Steps: {', '.join(q.steps)}")
            lines.append("")
        sections.append("\n".join(lines))

    # --- Section 7: Warnings ---
    warnings = []
    if state.history and state.history[-1].startswith(f"{char.id}"):
        warnings.append("*I just acted. I should wait to see what happens.*")
    recent = state.history[-5:] if state.history else []
    if sum(1 for e in recent if '"' in e or "says" in e.lower()) >= 4:
        warnings.append("*Lots of talking. Maybe time for action.*")
    if warnings:
        sections.append("## 💡 Reminders\n\n" + "\n".join(f"> {w}" for w in warnings))

    # --- Action Prompt ---
    sections.append("---\n\n**What do I do?**")

    return "\n\n".join(sections)


def build_casting_context(state: WorldState, location_id: str | None = None) -> str:
    """Build context for selecting and acting as one character.

    If location_id is provided and exists, scope selection to that location.
    Otherwise, scope to all characters.
    """
    sections = []

    scope_label = "all locations"
    scoped_chars = list(state.characters.values())

    if location_id and location_id in state.locations:
        scope_label = location_id
        scoped_chars = [c for c in state.characters.values() if c.location == location_id]

    if not scoped_chars:
        scoped_chars = list(state.characters.values())
        scope_label = "all locations"

    lines = ["## Turn Scope", "", f"Selection scope: **{scope_label}**", ""]
    sections.append("\n".join(lines))

    lines = ["## Candidates", ""]
    for c in scoped_chars:
        loc = state.locations.get(c.location)
        loc_name = loc.id if loc else c.location
        lines.append(f"### {c.id}")
        lines.append(f"- Location: {loc_name}")
        if c.goal:
            lines.append(f"- Goal: {c.goal}")
        if c.personality:
            lines.append(f"- Personality: {c.personality}")
        if c.knowledge:
            lines.append(f"- Recent knowledge: {'; '.join(c.knowledge[-3:])}")
        lines.append("")
    sections.append("\n".join(lines))

    lines = ["## Recent Events", ""]
    if state.history:
        for i, event in enumerate(state.history[-8:]):
            marker = "→" if i == len(state.history[-8:]) - 1 else "-"
            lines.append(f"{marker} {event}")
    else:
        lines.append("_No events yet._")
    sections.append("\n".join(lines))

    sections.append("---\n\nChoose one character and act now with a tool call including `character_id`.")
    return "\n\n".join(sections)

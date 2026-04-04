"""DM context builder — world state and last action for each turn."""
from __future__ import annotations

from src.core.models import WorldState


def build_dm_context(state: WorldState, last_action: dict | None = None) -> str:
    """Build the DM's context from current state and latest character action."""
    sections = []

    # --- Section 1: Story Context ---
    lines = ["## 📖 Story Context", ""]
    lines.append(f"**Turn:** {state.time}")
    sections.append("\n".join(lines))

    # --- Section 2: Last Character Action ---
    lines = ["## ⚡ Last Character Action", ""]
    if last_action:
        char_id = last_action.get("character_id", "unknown")
        tool = last_action.get("tool", "unknown")
        result = last_action.get("result") or {}
        lines.append(f"- Character: **{char_id}**")
        lines.append(f"- Tool: **{tool}**")
        if result.get("intent"):
            lines.append(f"- Intent: {result['intent']}")
        if result.get("message"):
            lines.append(f"- Result: {result['message']}")
        if result.get("status"):
            lines.append(f"- Status: {result['status']}")
    else:
        lines.append("- No prior character action. Establish the opening beat.")
    sections.append("\n".join(lines))

    # --- Section 3: Recent Events ---
    lines = ["## 📜 Recent Events", ""]
    if state.history:
        for i, event in enumerate(state.history[-10:]):
            marker = "→" if i == len(state.history[-10:]) - 1 else "-"
            lines.append(f"{marker} {event}")
    else:
        lines.append("_No events yet._")
    sections.append("\n".join(lines))

    # --- Section 4: Characters ---
    lines = ["## 👥 Characters", ""]
    for char in state.characters.values():
        loc = state.locations.get(char.location)
        loc_name = loc.id if loc else "unknown"

        try:
            from src.core.rules import get_health_status

            hs = get_health_status(char)
        except Exception:
            hs = "unknown"

        hp = getattr(char.stats, "hp", "?") if char.stats else "?"
        max_hp = getattr(char.stats, "max_hp", "?") if char.stats else "?"

        lines.append(f"**{char.id}** at {loc_name} — HP: {hp}/{max_hp} ({hs})")
        if char.goal:
            lines.append(f"  - 🎯 Goal: {char.goal}")
        lines.append("")
    sections.append("\n".join(lines))

    # --- Section 5: Active Quests ---
    if state.quests:
        lines = ["## 🗺️ Active Quests", ""]
        opportunities = []
        for q in state.quests.values():
            if str(getattr(q, "status", "active")).lower() not in (
                "completed",
                "failed",
            ):
                lines.append(f"**{q.title}**: {q.description}")
                # Check for quest advancement opportunities
                for char in state.characters.values():
                    char_loc = state.locations.get(char.location)
                    if char_loc:
                        loc_name = char_loc.id.lower()
                        quest_words = (
                            q.title.lower().split() + q.description.lower().split()
                        )
                        if any(w in loc_name for w in quest_words if len(w) > 4):
                            opportunities.append(
                                f"⚡ {char.id} at {char_loc.id} — relevant to '{q.title}'!"
                            )
                        if "hidden" in loc_name or "secret" in loc_name:
                            opportunities.append(
                                f"⚡ {char.id} in HIDDEN AREA — add reward/clue!"
                            )
        lines.append("")
        if opportunities:
            lines.append("**Opportunities:**")
            lines.extend(opportunities)
        if len(lines) > 2:
            sections.append("\n".join(lines))

    # --- Section 6: Locations ---
    lines = ["## 🏰 Locations", ""]
    for lid, loc in state.locations.items():
        present = [c.id for c in state.characters.values() if c.location == lid]
        present_str = f" — *{', '.join(present)} here*" if present else ""
        lines.append(f"**{loc.id}**{present_str}")
        if loc.features:
            lines.append(f"  - Features: {', '.join(loc.features)}")
        if loc.items:
            lines.append(f"  - Items: {', '.join(loc.items)}")
        if loc.connections:
            lines.append(f"  - Exits: {', '.join(loc.connections)}")
        lines.append("")
    sections.append("\n".join(lines))

    # --- Section 7: Warnings ---
    warnings = []
    for char in state.characters.values():
        if char.stats and char.stats.hp < char.stats.max_hp * 0.3:
            warnings.append(f"⚠️ {char.id} is badly wounded!")
    if warnings:
        sections.append("## ⚠️ Warnings\n\n" + "\n".join(warnings))

    # --- Action Prompt ---
    sections.append("---\n\n**What happens next in the world?**")

    return "\n\n".join(sections)

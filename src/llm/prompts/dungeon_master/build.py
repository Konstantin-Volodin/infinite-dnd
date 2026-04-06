# src/llm/prompts/dungeon_master/build.py
"""DM prompt builders - system prompt and context."""

from __future__ import annotations
from src.core.models import WorldState
from src.core.rules import get_health_status
from src.llm.prompts.loader import render


def dm_system() -> str:
    """Build the DM's system prompt."""
    return render("dungeon_master/system.jinja")


def dm_context(state: WorldState, last_action: dict | None = None) -> str:
    """Build the DM's context from current state and latest character action."""

    # Characters
    characters = []
    for char in state.characters.values():
        loc = state.locations.get(char.location)
        characters.append({
            "id": char.id,
            "loc_name": loc.id if loc else "unknown",
            "hp": char.stats.hp if char.stats else "?",
            "max_hp": char.stats.max_hp if char.stats else "?",
            "health_status": get_health_status(char),
            "goal": char.goal,
        })

    # Active quests
    quests = [
        q for q in state.quests.values()
        if str(getattr(q, "status", "active")).lower() not in ("completed", "failed")
    ]

    # Locations
    locations = []
    for lid, loc in state.locations.items():
        present = [c.id for c in state.characters.values() if c.location == lid]
        locations.append({
            "id": loc.id,
            "present": present,
            "features": loc.features,
            "items": loc.items,
            "connections": loc.connections,
        })

    # Warnings
    warnings: list[str] = []
    for char in state.characters.values():
        if char.stats and char.stats.hp < char.stats.max_hp * 0.3:
            warnings.append(f"{char.id} is badly wounded!")

    # Normalize last_action for template
    action_data = None
    if last_action:
        result = last_action.get("result") or {}
        action_data = {
            "character_id": last_action.get("character_id", "unknown"),
            "tool": last_action.get("tool", "unknown"),
            "result": {
                "intent": result.get("intent"),
                "message": result.get("message"),
                "status": result.get("status"),
            },
        }

    events = [e.text for e in state.history[-10:]]

    return render(
        "dungeon_master/context.jinja",
        last_action=action_data,
        events=events,
        characters=characters,
        quests=quests,
        locations=locations,
        warnings=warnings,
    )

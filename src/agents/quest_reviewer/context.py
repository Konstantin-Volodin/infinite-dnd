"""Quest reviewer prompt builders."""

from src.engine.state import WorldState
from src.agents.utils import render


def quest_reviewer_system() -> str:
    return render("quest_reviewer/identity.jinja")


def quest_reviewer_context(state: WorldState) -> str:
    quests = [
        q for q in state.quests.values()
        if str(getattr(q, "status", "active")).lower() not in ("completed", "failed")
    ]
    events = [e.text for e in state.history[-15:]]
    return render("quest_reviewer/state.jinja", quests=quests, events=events)

"""Time keeper prompt builders."""

from src.agents.utils import render


def time_keeper_system() -> str:
    return render("time_keeper/identity.jinja")


def time_keeper_context(events: list[str]) -> str:
    return render("time_keeper/state.jinja", events=events)

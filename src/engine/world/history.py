"""History helpers for world state."""

from src.engine.state import HistoryEvent, WorldState


def add_history(state: WorldState, text: str, location: str) -> None:
    """Append a history event to state. Caps history at 50 entries."""
    characters = [character.id for character in state.characters.values() if character.location == location]
    state.history.append(HistoryEvent(text=text, location=location, characters=characters))
    if len(state.history) > 50:
        state.history.pop(0)
# src/llm/tools/character/actions.py
"""character tools logic - defines how character actions affect the world state."""

from src.core.models import Character, WorldState
from src.core.state import add_history


def perform_action(char: Character, state: WorldState, description: str, target: str | None = None) -> str:
    """Perform a physical action, optionally targeting a person, item, or feature."""
    intent = f"{char.id} {description}"
    if target: intent += f" (targeting {target})"
    
    add_history(state, intent, char.location)
    return intent


def speak(char: Character, state: WorldState, message: str, target: str | None = None) -> str:
    """Say something, optionally directed at a target."""
    if target: intent = f'{char.id} says to {target}: "{message}"'
    else: intent = f'{char.id} says: "{message}"'
    
    add_history(state, intent, char.location)
    return intent


def travel(char: Character, state: WorldState, location: str) -> str:
    """Move to a connected location."""
    new_loc = state.locations.get(location)
    current_loc = state.locations.get(char.location)
    
    if not new_loc: 
        return f"Cannot travel to {location!r} - location not found."
    if location not in current_loc.connections:
        return f"Cannot reach {location!r} from {char.location!r}."
    
    add_history(state, f"{char.id} left from {current_loc.id}", current_loc.id)
    char.location = location
    add_history(state, f"{char.id} travelled to {new_loc.id}", new_loc.id)
    return f"Traveled to {new_loc.id}."

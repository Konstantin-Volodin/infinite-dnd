# src/llm/tools/character/actions.py
"""character tools logic - defines how character actions affect the world state."""

from src.engine.models import Character, WorldState
from src.engine.state import add_history


def action(char: Character, state: WorldState, description: str, target: str | None = None) -> str:
    intent = f"{char.id} {description}"
    if target: intent += f" (targeting {target})"
    
    add_history(state, intent, char.location)
    return intent


def speak(char: Character, state: WorldState, message: str, target: str | None = None) -> str:
    if target: intent = f'{char.id} says to {target}: "{message}"'
    else: intent = f'{char.id} says: "{message}"'
    
    add_history(state, intent, char.location)
    return intent


def travel(char: Character, state: WorldState, location: str) -> str:
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

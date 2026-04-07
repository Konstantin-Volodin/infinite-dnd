"""Character-driven world interactions."""

from src.engine.state import Character, WorldState
from src.engine.world.history import add_history
from src.engine.world.queries import resolve_location_id


def action(character: Character, state: WorldState, description: str, target: str | None = None) -> str:
    intent = f"{character.id} {description}"
    if target:
        intent += f" (targeting {target})"

    add_history(state, intent, character.location)
    return intent


def speak(character: Character, state: WorldState, message: str, target: str | None = None) -> str:
    if target:
        intent = f'{character.id} says to {target}: "{message}"'
    else:
        intent = f'{character.id} says: "{message}"'

    add_history(state, intent, character.location)
    return intent


def travel(character: Character, state: WorldState, location: str) -> str:
    current_location = state.locations.get(character.location)
    next_location_id = resolve_location_id(state, location)
    next_location = state.locations.get(next_location_id or "")

    if not next_location:
        return f"Cannot travel to {location!r} - location not found."
    if not current_location:
        return f"Cannot travel from {character.location!r} - current location not found."
    if next_location.id not in current_location.connections:
        return f"Cannot reach {next_location.id!r} from {character.location!r}."

    add_history(state, f"{character.id} left from {current_location.id}", current_location.id)
    character.location = next_location.id
    add_history(state, f"{character.id} travelled to {next_location.id}", next_location.id)
    return f"Traveled to {next_location.id}."


def wait(character: Character, state: WorldState) -> str:
    text = f"{character.id} waits."
    add_history(state, text, character.location)
    return text
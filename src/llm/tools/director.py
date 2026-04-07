"""director tools logic - selects a character and delegates to character tools."""


from src.core.models import Character, WorldState
from src.core.utils import slugify
from src.llm.tools.character import action as character_action
from src.llm.tools.character import speak as character_speak
from src.llm.tools.character import travel as character_travel


def _resolve_character(state: WorldState, character_id: str) -> Character | None:
    if character_id in state.characters:
        return state.characters[character_id]

    target = slugify(character_id)
    for char in state.characters.values():
        if slugify(char.id) == target:
            return char
    return None


def action(state: WorldState, character_id: str, description: str, target: str | None = None) -> str:
    char = _resolve_character(state, character_id)
    if not char:
        return f"Cannot act as {character_id!r} - character not found."
    return character_action(char, state, description, target)


def speak(state: WorldState, character_id: str, message: str, target: str | None = None) -> str:
    char = _resolve_character(state, character_id)
    if not char:
        return f"Cannot speak as {character_id!r} - character not found."
    return character_speak(char, state, message, target)


def travel(state: WorldState, character_id: str, location: str) -> str:
    char = _resolve_character(state, character_id)
    if not char:
        return f"Cannot travel as {character_id!r} - character not found."
    return character_travel(char, state, location)
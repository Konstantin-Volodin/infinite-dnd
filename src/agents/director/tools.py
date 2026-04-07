# src/llm/tools/director.py
"""director tools logic - selects a character and delegates to character tools."""

from src.engine.world.queries import resolve_character
from src.engine.state import Character, WorldState
from src.agents.character.tools import action as character_action
from src.agents.character.tools import speak as character_speak
from src.agents.character.tools import travel as character_travel


def action(state: WorldState, character_id: str, description: str, target: str | None = None) -> str:
    char = resolve_character(state, character_id)
    if not char:
        return f"Cannot act as {character_id!r} - character not found."
    return character_action(char, state, description, target)


def speak(state: WorldState, character_id: str, message: str, target: str | None = None) -> str:
    char = resolve_character(state, character_id)
    if not char:
        return f"Cannot speak as {character_id!r} - character not found."
    return character_speak(char, state, message, target)


def travel(state: WorldState, character_id: str, location: str) -> str:
    char = resolve_character(state, character_id)
    if not char:
        return f"Cannot travel as {character_id!r} - character not found."
    return character_travel(char, state, location)
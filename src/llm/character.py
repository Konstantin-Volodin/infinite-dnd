# src/llm/character.py
"""Agent for impersonating characters."""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from src.llm.server import create_model
from src.core.models import Character, WorldState
from src.llm.prompts.character.build import character_system, character_context
import src.llm.tools.character.actions as actions


@dataclass
class CharacterDeps:
    char: Character
    state: WorldState


agent = Agent(
    model=create_model(),
    deps_type=CharacterDeps,
    output_type=str,
    instructions="You are a character in a D&D game.",
)


@agent.system_prompt
def identity(ctx: RunContext[CharacterDeps]) -> str:
    return character_system(ctx.deps.char)


@agent.instructions
def context(ctx: RunContext[CharacterDeps]) -> str:
    return character_context(ctx.deps.char, ctx.deps.state)


@agent.tool
def perform_action(ctx: RunContext[CharacterDeps], description: str, target: str | None = None) -> str:
    """describe what you want to do and how you want to do it. can target person, item, or feature. be specific and detailed."""
    return actions.perform_action(ctx.deps.char, ctx.deps.state, description, target)


@agent.tool
def speak(ctx: RunContext[CharacterDeps], message: str, target: str | None = None) -> str:
    """say something. can be targeted dialogue or thinking out loud."""
    return actions.speak(ctx.deps.char, ctx.deps.state, message, target)


@agent.tool
def travel(ctx: RunContext[CharacterDeps], location: str) -> str:
    """travel to a connected location."""
    return actions.travel(ctx.deps.char, ctx.deps.state, location)

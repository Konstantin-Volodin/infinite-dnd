# src/llm/character.py
"""Agent for impersonating characters."""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from src.llm.server import create_model
from src.llm.prompts import character_system, character_context
from src.llm.tools import action, speak, travel
from src.core.models import Character, WorldState


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

# context
@agent.system_prompt
def identity(ctx: RunContext[CharacterDeps]) -> str:
    return character_system(ctx.deps.char)

@agent.instructions
def context(ctx: RunContext[CharacterDeps]) -> str:
    return character_context(ctx.deps.char, ctx.deps.state)


# tools
@agent.tool
def action(ctx: RunContext[CharacterDeps], description: str, target: str | None = None) -> str:
    """describe what you want to do and how you want to do it. can target person, item, or feature. be specific and detailed."""
    return action(ctx.deps.char, ctx.deps.state, description, target)

@agent.tool
def speak(ctx: RunContext[CharacterDeps], message: str, target: str | None = None) -> str:
    """say something. can be targeted dialogue or thinking out loud."""
    return speak(ctx.deps.char, ctx.deps.state, message, target)

@agent.tool
def travel(ctx: RunContext[CharacterDeps], location: str) -> str:
    """travel to a connected location."""
    return travel(ctx.deps.char, ctx.deps.state, location)

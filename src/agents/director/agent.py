# src/llm/director.py
"""Agent for choosing a character to act."""

from dataclasses import dataclass
from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.state import WorldState
from src.agents.utils import create_model
from .context import director_context, director_system
from .tools import action as director_action, speak as director_speak, travel as director_travel


@dataclass
class DirectorDeps:
    state: WorldState
    location_id: str | None = None

agent: Agent[DirectorDeps, str] = Agent(
    model=create_model(),
    deps_type=DirectorDeps,
    output_type=ToolOutput(str, name="done"),
    instructions="You are directing which character acts next in a D&D game.",
)


# context
@agent.system_prompt
def identity(_: RunContext[DirectorDeps]) -> str:
    return director_system()

@agent.instructions
def context(ctx: RunContext[DirectorDeps]) -> str:
    return director_context(ctx.deps.state, ctx.deps.location_id)


# tools
@agent.tool
def action(
    ctx: RunContext[DirectorDeps],
    character_id: str,
    description: str,
    target: str | None = None,
) -> str:
    """choose a character and have them take a deliberate action."""
    return director_action(ctx.deps.state, character_id=character_id, description=description, target=target)

@agent.tool
def speak(
    ctx: RunContext[DirectorDeps],
    character_id: str,
    message: str,
    target: str | None = None,
) -> str:
    """choose a character and have them say something."""
    return director_speak(ctx.deps.state, character_id=character_id, message=message, target=target)

@agent.tool
def travel(
    ctx: RunContext[DirectorDeps], 
    character_id: str, 
    location: str
) -> str:
    """choose a character and have them travel to a connected location."""
    return director_travel(ctx.deps.state, character_id=character_id, location=location)
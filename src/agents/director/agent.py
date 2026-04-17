"""Agent for choosing a character to act."""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.state import WorldOperations, WorldState, resolve_character
from src.agents.action_resolver.agent import ActionResolverDeps, agent as action_resolver_agent
from src.agents.utils import create_model
from .context import director_context, director_system


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


@agent.system_prompt
def identity(_: RunContext[DirectorDeps]) -> str:
    return director_system()


@agent.instructions
def context(ctx: RunContext[DirectorDeps]) -> str:
    return director_context(ctx.deps.state, ctx.deps.location_id)


@agent.tool
async def action(
    ctx: RunContext[DirectorDeps],
    character_id: str,
    description: str,
    target: str | None = None,
) -> str:
    """choose a character and have them take a deliberate action."""
    char = resolve_character(ctx.deps.state, character_id)
    if not char:
        return f"Cannot act as {character_id!r} — character not found."
    prompt = f"Resolve this action: {description}"
    if target:
        prompt += f" (target: {target})"
    result = await action_resolver_agent.run(
        prompt,
        deps=ActionResolverDeps(char=char, state=ctx.deps.state, description=description, target=target),
        usage=ctx.usage,
    )
    return result.output


@agent.tool
def speak(
    ctx: RunContext[DirectorDeps],
    character_id: str,
    message: str,
    target: str | None = None,
) -> str:
    """choose a character and have them say something."""
    char = resolve_character(ctx.deps.state, character_id)
    if not char:
        return f"Cannot speak as {character_id!r} — character not found."
    return WorldOperations(ctx.deps.state).speak(char.id, message, target)


@agent.tool
def travel(
    ctx: RunContext[DirectorDeps],
    character_id: str,
    location: str,
) -> str:
    """choose a character and have them travel to a connected location."""
    char = resolve_character(ctx.deps.state, character_id)
    if not char:
        return f"Cannot travel as {character_id!r} — character not found."
    return WorldOperations(ctx.deps.state).move_character(char.id, location)

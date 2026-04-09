# src/llm/character.py
"""Agent for impersonating characters."""

import logging
from dataclasses import dataclass, replace, field

from pydantic_ai import Agent, RunContext, ToolOutput
from pydantic_ai.tools import ToolDefinition

from src.engine.state import Character, WorldState
from src.engine.world.interactions import wait
from src.engine.world.queries import characters_in_location, connected_location_ids
from src.agents.action_resolver.agent import ActionResolverDeps, agent as action_resolver_agent
from .context import character_context, character_system
from src.agents.utils import create_model
from .tools import speak as character_speak, travel as character_travel



@dataclass
class CharacterDeps:
    char: Character
    state: WorldState
    failed_travels: list[str] = field(default_factory=list)


def _speak_targets(ctx: RunContext[CharacterDeps]) -> list[str]:
    return [c.id for c in characters_in_location(ctx.deps.state, ctx.deps.char.location, exclude_character_id=ctx.deps.char.id)]


def _travel_options(ctx: RunContext[CharacterDeps]) -> list[str]:
    return connected_location_ids(ctx.deps.state, ctx.deps.char.location)


def _prepare_output_tools(
    ctx: RunContext[CharacterDeps],
    tool_defs: list[ToolDefinition],
) -> list[ToolDefinition]:
    targets = _speak_targets(ctx)
    options = _travel_options(ctx)

    result: list[ToolDefinition] = []
    for td in tool_defs:
        if td.name == "speak":
            hint = f"Valid targets: {', '.join(targets)}." if targets else "No one else here — leave target empty."
            result.append(replace(td, description=f"say something. {hint}"))
        elif td.name == "travel":
            if options:
                result.append(replace(td, description=f"travel to a connected location. Valid ids: {', '.join(options)}."))
        else:
            result.append(td)
    return result


# ── output tools ─────────────────────────────────────────────────────────

async def action_output(
    ctx: RunContext[CharacterDeps],
    description: str,
    target: str | None = None,
) -> str:
    """describe what you want to do and how you want to do it. this tool resolves consequences and returns the world response."""
    prompt = f"Resolve this action: {description}"
    if target:
        prompt += f" (target: {target})"

    logging.info(f"  [action_resolver] starting for {ctx.deps.char.id}: {description!r}")
    result = await action_resolver_agent.run(
        prompt,
        deps=ActionResolverDeps(char=ctx.deps.char, state=ctx.deps.state, description=description, target=target),
        usage=ctx.usage,
    )
    logging.info(f"  [action_resolver] finished: {result.output!r}")
    return result.output


def speak_output(
    ctx: RunContext[CharacterDeps],
    message: str,
    target: str | None = None,
) -> str:
    """say something. can be targeted dialogue or thinking out loud."""
    targets = _speak_targets(ctx)
    if target and target not in targets:
        hint = f"Valid targets: {', '.join(targets)}." if targets else "No one else is here."
        return f"Cannot speak to {target!r}. {hint}"
    return character_speak(ctx.deps.char, ctx.deps.state, message, target)


def travel_output(
    ctx: RunContext[CharacterDeps],
    location: str,
) -> str:
    """travel to a connected location."""
    options = _travel_options(ctx)
    if location not in options:
        ctx.deps.failed_travels.append(location)
        if options:
            return f"Cannot travel to {location!r}. Valid: {', '.join(options)}."
        return "No travel options right now. Use action or wait instead."
    return character_travel(ctx.deps.char, ctx.deps.state, location)


def wait_output(ctx: RunContext[CharacterDeps]) -> str:
    """do nothing for now and wait to see what happens next."""
    return wait(ctx.deps.char, ctx.deps.state)


CHARACTER_RESPONSE_OUTPUTS = [
    ToolOutput(speak_output, name="speak"),
    ToolOutput(wait_output, name="wait"),
]

agent: Agent[CharacterDeps, str] = Agent(
    model=create_model(),
    deps_type=CharacterDeps,
    output_type=[
        ToolOutput(action_output, name="action"),
        ToolOutput(speak_output, name="speak"),
        ToolOutput(travel_output, name="travel"),
        ToolOutput(wait_output, name="wait"),
    ],
    prepare_output_tools=_prepare_output_tools,
    instructions="You are a character in a D&D game.",
)


# context
@agent.system_prompt
def identity(ctx: RunContext[CharacterDeps]) -> str:
    return character_system(ctx.deps.char)

@agent.instructions
def context(ctx: RunContext[CharacterDeps]) -> str:
    return character_context(ctx.deps.char, ctx.deps.state)

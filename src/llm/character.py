# src/llm/character.py
"""Agent for impersonating characters."""

from copy import deepcopy
from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext, ToolOutput
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.tools import ToolDefinition

from src.core.models import Character, WorldState
from src.core.state import add_history
from src.llm.action_resolver import ActionResolverDeps, agent as action_resolver_agent
from src.llm.prompts import character_context, character_system
from src.llm.server import create_model
from src.llm.tools import character_speak, character_travel
from src.llm.tools.world import characters_in_location, connected_location_ids


@dataclass
class CharacterDeps:
    char: Character
    state: WorldState
    failed_travels: list[str] = field(default_factory=list)


def _available_speak_targets(ctx: RunContext[CharacterDeps]) -> list[str]:
    return [
        character.id
        for character in characters_in_location(
            ctx.deps.state,
            ctx.deps.char.location,
            exclude_character_id=ctx.deps.char.id,
        )
    ]


def _available_travel_locations(ctx: RunContext[CharacterDeps]) -> list[str]:
    return connected_location_ids(ctx.deps.state, ctx.deps.char.location)


def _prepare_speak_tool(ctx: RunContext[CharacterDeps], tool_def: ToolDefinition) -> ToolDefinition:
    prepared = deepcopy(tool_def)
    targets = _available_speak_targets(ctx)
    prepared.description = (
        "say something. leave target empty to speak out loud. "
        + (
            f"Valid target ids right now: {', '.join(targets)}."
            if targets
            else "No other NPCs are here right now."
        )
        + " If you want someone else, use action to find or reveal them first."
    )

    target_schema = prepared.parameters_json_schema["properties"]["target"]
    if targets:
        for branch in target_schema.get("anyOf", []):
            if branch.get("type") == "string":
                branch["enum"] = targets
                branch["description"] = f"Optional. Use one of: {', '.join(targets)}."
    else:
        prepared.parameters_json_schema["properties"]["target"] = {
            "type": "null",
            "default": None,
            "description": "No one else is here right now. Leave target empty.",
        }
    return prepared


def _prepare_travel_tool(ctx: RunContext[CharacterDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    options = _available_travel_locations(ctx)
    if not options:
        return None

    prepared = deepcopy(tool_def)
    prepared.description = (
        f"travel to a connected location. Valid location ids right now: {', '.join(options)}. "
        "If you want somewhere else, use action to discover it first."
    )
    location_schema = prepared.parameters_json_schema["properties"]["location"]
    location_schema["enum"] = options
    location_schema["description"] = f"Use one of: {', '.join(options)}."
    return prepared


def _prepare_output_tools(
    ctx: RunContext[CharacterDeps],
    tool_defs: list[ToolDefinition],
) -> list[ToolDefinition]:
    prepared_defs: list[ToolDefinition] = []
    for tool_def in tool_defs:
        if tool_def.name == "speak":
            prepared_defs.append(_prepare_speak_tool(ctx, tool_def))
        elif tool_def.name == "travel":
            prepared = _prepare_travel_tool(ctx, tool_def)
            if prepared is not None:
                prepared_defs.append(prepared)
        else:
            prepared_defs.append(tool_def)
    return prepared_defs


def _validate_speak_target(ctx: RunContext[CharacterDeps], target: str | None = None) -> None:
    if target is None:
        return

    options = _available_speak_targets(ctx)
    if target not in options:
        if options:
            raise ModelRetry(
                f"Invalid speak target {target!r}. Right now you can only target: {', '.join(options)}. "
                "If you want someone else, use action to find or reveal them first."
            )
        raise ModelRetry(
            "No one else is here right now. Leave speak.target empty to talk out loud, "
            "or use action to find someone first."
        )


async def action_output(
    ctx: RunContext[CharacterDeps],
    description: str,
    target: str | None = None,
) -> str:
    """describe what you want to do and how you want to do it. this tool resolves consequences and returns the world response."""
    prompt = f"Resolve this action: {description}"
    if target:
        prompt += f" (target: {target})"

    result = await action_resolver_agent.run(
        prompt,
        deps=ActionResolverDeps(char=ctx.deps.char, state=ctx.deps.state, description=description, target=target),
        usage=ctx.usage,
    )
    return result.output


def speak_output(
    ctx: RunContext[CharacterDeps],
    message: str,
    target: str | None = None,
) -> str:
    """say something. can be targeted dialogue or thinking out loud."""
    _validate_speak_target(ctx, target)
    return character_speak(ctx.deps.char, ctx.deps.state, message, target)


def travel_output(
    ctx: RunContext[CharacterDeps],
    location: str,
) -> str:
    """travel to a connected location."""
    options = _available_travel_locations(ctx)
    if location not in options:
        ctx.deps.failed_travels.append(location)
        if options:
            return (
                f"Cannot travel to {location!r}. Right now you can only travel to: {', '.join(options)}. "
                "If you want somewhere else, use action to discover it first."
            )
        return "There are no connected travel options right now. Use action or wait instead."
    return character_travel(ctx.deps.char, ctx.deps.state, location)


def wait_output(ctx: RunContext[CharacterDeps]) -> str:
    """do nothing for now and wait to see what happens next."""
    text = f"{ctx.deps.char.id} waits."
    add_history(ctx.deps.state, text, ctx.deps.char.location)
    return text


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
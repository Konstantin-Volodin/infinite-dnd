"""Character agent: emits typed intents. Does not mutate state."""

from dataclasses import dataclass, replace

from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.tools import ToolDefinition

from src.engine.state import Character, WorldState, characters_in_location, connected_location_ids
from src.agents.utils import create_model
from .context import character_context, character_system
from .tools import Action, CharacterTool, Speak, Travel, Wait


@dataclass
class CharacterDeps:
    char: Character
    state: WorldState


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


def speak_output(
    ctx: RunContext[CharacterDeps],
    message: str,
    target: str | None = None,
) -> Speak:
    """say something. can be targeted dialogue or thinking out loud."""
    targets = _speak_targets(ctx)
    if target and target not in targets:
        hint = f"Valid targets: {', '.join(targets)}." if targets else "No one else is here."
        raise ModelRetry(f"Cannot speak to {target!r}. {hint}")
    return Speak(actor=ctx.deps.char.id, message=message, target=target)


def travel_output(
    ctx: RunContext[CharacterDeps],
    location: str,
) -> Travel:
    """travel to a connected location, or propose a new one for the DM to introduce."""
    return Travel(actor=ctx.deps.char.id, destination=location)


def wait_output(ctx: RunContext[CharacterDeps]) -> Wait:
    """do nothing for now and wait to see what happens next."""
    return Wait(actor=ctx.deps.char.id)


def action_output(
    ctx: RunContext[CharacterDeps],
    description: str,
    target: str | None = None,
) -> Action:
    """take a concrete action — search, examine, attempt, interact, discover. describe what and how. use this when you can make progress, not just when speak/travel don't fit."""
    return Action(actor=ctx.deps.char.id, description=description, target=target)


CHARACTER_RESPONSE_OUTPUTS = [
    ToolOutput(speak_output, name="speak"),
    ToolOutput(wait_output, name="wait"),
]

agent: Agent[CharacterDeps, CharacterTool] = Agent(
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


@agent.system_prompt
def identity(ctx: RunContext[CharacterDeps]) -> str:
    return character_system(ctx.deps.char)


@agent.instructions
def context(ctx: RunContext[CharacterDeps]) -> str:
    return character_context(ctx.deps.char, ctx.deps.state)

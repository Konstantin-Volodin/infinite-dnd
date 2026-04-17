"""Agent for resolving character actions into mechanical world-state changes."""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.state import Character, WorldOperations, WorldState, slugify
from src.agents.utils import create_model
from .context import action_resolver_context, action_resolver_system


@dataclass
class ActionResolverDeps:
    char: Character
    state: WorldState
    description: str
    target: str | None = None


agent: Agent[ActionResolverDeps, str] = Agent(
    model=create_model(),
    deps_type=ActionResolverDeps,
    output_type=ToolOutput(str, name="done"),
    instructions="Resolve exactly one character action into concrete state changes.",
)


@agent.system_prompt
def identity(_: RunContext[ActionResolverDeps]) -> str:
    return action_resolver_system()


@agent.instructions
def context(ctx: RunContext[ActionResolverDeps]) -> str:
    return action_resolver_context(
        ctx.deps.char,
        ctx.deps.state,
        description=ctx.deps.description,
        target=ctx.deps.target,
    )


def _ops(ctx: RunContext[ActionResolverDeps]) -> WorldOperations:
    return WorldOperations(ctx.deps.state)


@agent.tool
def remember(
    ctx: RunContext[ActionResolverDeps],
    knowledge: str,
    character_id: str | None = None,
) -> str:
    """add a concrete piece of knowledge to the acting character or another known character."""
    return _ops(ctx).add_knowledge(character_id or ctx.deps.char.id, knowledge)


@agent.tool
def add_detail(
    ctx: RunContext[ActionResolverDeps],
    detail: str,
    location: str | None = None,
) -> str:
    """add a newly discovered concrete detail to the current location or another known location."""
    return _ops(ctx).modify_location(location or ctx.deps.char.location, add_feature=detail)


@agent.tool
def discover_exit(
    ctx: RunContext[ActionResolverDeps],
    name: str,
    description: str,
    location_id: str | None = None,
    anchor_location: str | None = None,
) -> str:
    """add a newly discovered reachable location and connect it to the current place."""
    anchor = anchor_location or ctx.deps.char.location
    return _ops(ctx).add_location(location_id or slugify(name), description=description, connections=[anchor])


@agent.tool
def adjust_hp(
    ctx: RunContext[ActionResolverDeps],
    delta: int,
    character_id: str | None = None,
    reason: str | None = None,
) -> str:
    """change a character's HP by a small signed amount when the action causes harm or recovery."""
    target = character_id or ctx.deps.char.id
    ops = _ops(ctx)
    return ops.heal(target, delta) if delta >= 0 else ops.damage(target, -delta)


@agent.tool
def update_quest(
    ctx: RunContext[ActionResolverDeps],
    quest_id: str,
    status: str,
) -> str:
    """update a quest status when the action clearly advances or completes it."""
    return _ops(ctx).advance_quest(quest_id, new_status=status)


@agent.tool
def take(
    ctx: RunContext[ActionResolverDeps],
    item_name: str,
    character_id: str | None = None,
) -> str:
    """move an item from a location into a character's inventory."""
    return _ops(ctx).take_item(character_id or ctx.deps.char.id, item_name)


@agent.tool
def drop(
    ctx: RunContext[ActionResolverDeps],
    item_name: str,
    character_id: str | None = None,
) -> str:
    """move an item from a character's inventory into a location."""
    return _ops(ctx).drop_item(character_id or ctx.deps.char.id, item_name)


@agent.tool
def create_item(
    ctx: RunContext[ActionResolverDeps],
    item_name: str,
    location: str | None = None,
) -> str:
    """place a new item in a location. use when the action reveals or produces a tangible object."""
    return _ops(ctx).create_item(item_name, location or ctx.deps.char.location)


@agent.tool
def create_npc(
    ctx: RunContext[ActionResolverDeps],
    name: str,
    role: str = "",
    goal: str = "",
    backstory: str = "",
    location: str | None = None,
) -> str:
    """add a new NPC to the world. use when the action reveals or encounters a new character."""
    return _ops(ctx).spawn_npc(
        slugify(name),
        role=role,
        location_id=location or ctx.deps.char.location,
        backstory=backstory,
        goal=goal,
    )

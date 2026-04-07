"""Agent for resolving character actions into mechanical world-state changes."""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.models import Character, WorldState
from src.engine.world import add_location_feature, adjust_hit_points, create_item as world_create_item, drop_item
from src.engine.world import discover_location, spawn_npc as world_spawn_npc
from src.engine.world import remember as remember_fact
from src.engine.world import take_item, update_quest_status
from src.llm.prompts import action_resolver_context, action_resolver_system
from src.llm.server import create_model


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


@agent.tool
def remember(
    ctx: RunContext[ActionResolverDeps],
    knowledge: str,
    character_id: str | None = None,
) -> str:
    """add a concrete piece of knowledge to the acting character or another known character."""
    target_character = character_id or ctx.deps.char.id
    return remember_fact(ctx.deps.state, target_character, knowledge)


@agent.tool
def add_detail(
    ctx: RunContext[ActionResolverDeps],
    detail: str,
    location: str | None = None,
) -> str:
    """add a newly discovered concrete detail to the current location or another known location."""
    target_location = location or ctx.deps.char.location
    return add_location_feature(ctx.deps.state, detail, location=target_location)


@agent.tool
def discover_exit(
    ctx: RunContext[ActionResolverDeps],
    name: str,
    description: str,
    location_id: str | None = None,
    anchor_location: str | None = None,
) -> str:
    """add a newly discovered reachable location and connect it to the current place."""
    return discover_location(
        ctx.deps.state,
        name=name,
        description=description,
        location_id=location_id,
        anchor_location=anchor_location or ctx.deps.char.location,
    )


@agent.tool
def adjust_hp(
    ctx: RunContext[ActionResolverDeps],
    delta: int,
    character_id: str | None = None,
    reason: str | None = None,
) -> str:
    """change a character's HP by a small signed amount when the action causes harm or recovery."""
    target_character = character_id or ctx.deps.char.id
    return adjust_hit_points(ctx.deps.state, target_character, delta=delta, reason=reason)


@agent.tool
def update_quest(
    ctx: RunContext[ActionResolverDeps],
    quest_id: str,
    status: str,
) -> str:
    """update a quest status when the action clearly advances or completes it."""
    return update_quest_status(ctx.deps.state, quest_id, status=status)


@agent.tool
def take(
    ctx: RunContext[ActionResolverDeps],
    item_name: str,
    character_id: str | None = None,
    location: str | None = None,
) -> str:
    """move an item from a location into a character's inventory."""
    target_character = character_id or ctx.deps.char.id
    return take_item(ctx.deps.state, target_character, item_name=item_name, location=location)


@agent.tool
def drop(
    ctx: RunContext[ActionResolverDeps],
    item_name: str,
    character_id: str | None = None,
    location: str | None = None,
) -> str:
    """move an item from a character's inventory into a location."""
    target_character = character_id or ctx.deps.char.id
    return drop_item(ctx.deps.state, target_character, item_name=item_name, location=location)


@agent.tool
def create_item(
    ctx: RunContext[ActionResolverDeps],
    item_name: str,
    description: str | None = None,
    location: str | None = None,
) -> str:
    """place a new item in a location. use when the action reveals or produces a tangible object."""
    target_location = location or ctx.deps.char.location
    return world_create_item(ctx.deps.state, item_name=item_name, description=description, location=target_location)


@agent.tool
def create_npc(
    ctx: RunContext[ActionResolverDeps],
    name: str,
    description: str,
    role: str | None = None,
    goal: str | None = None,
    location: str | None = None,
) -> str:
    """add a new NPC to the world. use when the action reveals or encounters a new character."""
    target_location = location or ctx.deps.char.location
    return world_spawn_npc(ctx.deps.state, name=name, description=description, role=role, location=target_location, goal=goal)

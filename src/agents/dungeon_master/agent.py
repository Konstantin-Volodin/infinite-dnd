"""Agent for narrating and updating the world as the dungeon master."""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.state import HistoryEvent, WorldOperations, WorldState, slugify
from src.agents.utils import create_model
from .context import dm_context, dm_system


@dataclass
class DungeonMasterDeps:
    state: WorldState
    last_action: dict[str, Any] | None = None
    narrate_location: str = ""


agent: Agent[DungeonMasterDeps, str] = Agent(
    model=create_model(),
    deps_type=DungeonMasterDeps,
    output_type=ToolOutput(str, name="done"),
    instructions="You are the dungeon master in a D&D game.",
)


@agent.system_prompt
def identity(_: RunContext[DungeonMasterDeps]) -> str:
    return dm_system()


@agent.instructions
def context(ctx: RunContext[DungeonMasterDeps]) -> str:
    return dm_context(ctx.deps.state, last_action=ctx.deps.last_action)


@agent.tool
def narrate(
    ctx: RunContext[DungeonMasterDeps],
    content: str,
    prompts_character: str | None = None,
) -> str:
    """describe what happens in the world without speaking for characters."""
    ctx.deps.state.history.append(HistoryEvent(text=content, location=ctx.deps.narrate_location))
    return content


@agent.tool
def create(
    ctx: RunContext[DungeonMasterDeps],
    type: Literal["location", "item", "npc"],
    name: str,
    description: str,
    location: str | None = None,
    role: str | None = None,
    goal: str | None = None,
) -> str:
    """add a location, item, or NPC to the world."""
    ops = WorldOperations(ctx.deps.state)
    slug = slugify(name)
    if type == "location":
        connections = [location] if location else []
        return ops.add_location(slug, description=description, connections=connections)
    if type == "item":
        if not location:
            return "Cannot create item — location is required."
        return ops.create_item(name, location)
    if type == "npc":
        if not location:
            return "Cannot create NPC — location is required."
        return ops.spawn_npc(slug, role=role or "", location_id=location, backstory=description, goal=goal or "")
    return f"Unknown create type: {type!r}."


@agent.tool
def modify(
    ctx: RunContext[DungeonMasterDeps],
    action: Literal["update_quest", "remove_npc", "update_location"],
    target_id: str,
    status: str | None = None,
    reason: str | None = None,
) -> str:
    """change a quest, NPC, or location in the world state."""
    ops = WorldOperations(ctx.deps.state)
    if action == "update_quest":
        if not status:
            return "Cannot update a quest without a status."
        return ops.advance_quest(target_id, new_status=status)
    if action == "remove_npc":
        return ops.delete_npc(target_id, reason=reason or "")
    if action == "update_location":
        return ops.modify_location(target_id, description=reason)
    return f"Unknown modify action: {action!r}."

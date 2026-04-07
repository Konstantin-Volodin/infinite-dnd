# src/llm/dungeon_master.py
"""Agent for narrating and updating the world as the dungeon master."""

from dataclasses import dataclass
from typing import Any, Literal
from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.state import WorldState
from src.llm.prompts import dm_context, dm_system
from src.llm.server import create_model
from src.llm.tools import dm_create, dm_modify, dm_narrate


@dataclass
class DungeonMasterDeps:
    state: WorldState
    last_action: dict[str, Any] | None = None
    narrate_location: str = ""
    narrated: bool = False
    created: bool = False
    modified: bool = False


def _claim_tool(ctx: RunContext[DungeonMasterDeps], field: str, blocked_message: str) -> str | None:
    if getattr(ctx.deps, field):
        return blocked_message
    setattr(ctx.deps, field, True)
    return None

agent: Agent[DungeonMasterDeps, str] = Agent(
    model=create_model(),
    deps_type=DungeonMasterDeps,
    output_type=ToolOutput(str, name="done"),
    instructions="You are the dungeon master in a D&D game.",
)


# context
@agent.system_prompt
def identity(_: RunContext[DungeonMasterDeps]) -> str:
    return dm_system()

@agent.instructions
def context(ctx: RunContext[DungeonMasterDeps]) -> str:
    return dm_context(ctx.deps.state, last_action=ctx.deps.last_action)


# tools
@agent.tool
def narrate(
    ctx: RunContext[DungeonMasterDeps],
    content: str,
    prompts_character: str | None = None,
) -> str:
    """describe what happens in the world without speaking for characters."""
    blocked = _claim_tool(ctx, "narrated", "Narration already recorded for this DM run. Call done now.")
    if blocked:
        return blocked
    return dm_narrate(ctx.deps.state, content, location=ctx.deps.narrate_location)

@agent.tool
def create(
    ctx: RunContext[DungeonMasterDeps],
    type: Literal["location", "item", "npc"],
    name: str,
    description: str,
    id: str | None = None,
    location: str | None = None,
    role: str | None = None,
    goal: str | None = None,
) -> str:
    """add a location, item, or NPC to the world."""
    blocked = _claim_tool(ctx, "created", "Creation already handled for this DM run. Call done now.")
    if blocked:
        return blocked
    return dm_create(
        ctx.deps.state,
        type=type,
        name=name,
        description=description,
        id=id,
        location=location,
        role=role,
        goal=goal,
    )

@agent.tool
def modify(
    ctx: RunContext[DungeonMasterDeps],
    action: Literal["update_quest", "remove_npc", "update_location"],
    target_id: str,
    status: str | None = None,
    reason: str | None = None,
) -> str:
    """change a quest, NPC, or location in the world state."""
    blocked = _claim_tool(ctx, "modified", "Modification already handled for this DM run. Call done now.")
    if blocked:
        return blocked
    return dm_modify(
        ctx.deps.state,
        action=action,
        target_id=target_id,
        status=status,
        reason=reason,
    )
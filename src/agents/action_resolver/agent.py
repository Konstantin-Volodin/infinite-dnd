"""Resolver: the sole writer to world state.

Public entry: `resolve(intent, state, usage=None) -> str`.
Deterministic dispatch for structured intents; an internal LLM sub-agent
(`_action_agent`) handles free-form Action tool.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic_ai import Agent, RunContext, ToolOutput
from pydantic_ai.usage import RunUsage

from src.engine.state import (
    Character,
    HistoryEvent,
    WorldOperations,
    WorldState,
    slugify,
)
from src.agents.character.tools import Action, Attack, CharacterTool, Speak, Travel, Wait
from src.agents.dm.tools import Create, Modify
from src.agents.utils import create_model
from src.interface.session_log import Logger
from .context import action_resolver_context, action_resolver_system


AnyTool = CharacterTool | Create | Modify


# ============================================================
# Public entry
# ============================================================

async def resolve(tool: AnyTool, state: WorldState, usage: RunUsage | None = None, logger: Logger | None = None) -> str:
    """Execute a tool call against world state. Single writer surface."""
    result = await _dispatch(tool, state, usage, logger)
    _apply_self_updates(tool, state)
    if logger:
        subject = getattr(tool, "actor", None) or getattr(tool, "target_id", None) or getattr(tool, "name", None)
        logger.log_event("resolved", tool=type(tool).__name__, subject=subject, result=result)
    return result


def _apply_self_updates(tool: AnyTool, state: WorldState) -> None:
    """Deterministically apply a character tool's optional self-updates (remember/new_goal). No extra LLM call."""
    actor = getattr(tool, "actor", None)
    if not actor or actor not in state.characters:
        return
    ops = WorldOperations(state)
    if remember := getattr(tool, "remember", None):
        ops.add_knowledge(actor, remember)
    if new_goal := getattr(tool, "new_goal", None):
        ops.set_goal(actor, new_goal)


async def _dispatch(tool: AnyTool, state: WorldState, usage: RunUsage | None, logger: Logger | None) -> str:
    if isinstance(tool, Speak):
        return _resolve_speak(tool, state)
    if isinstance(tool, Travel):
        return _resolve_travel(tool, state)
    if isinstance(tool, Wait):
        return _resolve_wait(tool, state)
    if isinstance(tool, Attack):
        return _resolve_attack(tool, state)
    if isinstance(tool, Create):
        return _resolve_create(tool, state)
    if isinstance(tool, Modify):
        return _resolve_modify(tool, state)
    if isinstance(tool, Action):
        return await _resolve_action(tool, state, usage, logger)
    raise TypeError(f"Unknown tool: {tool!r}")


# ============================================================
# Deterministic dispatch
# ============================================================

def _resolve_speak(tool: Speak, state: WorldState) -> str:
    return WorldOperations(state).speak(tool.actor, tool.message, tool.target)


def _resolve_travel(tool: Travel, state: WorldState) -> str:
    return WorldOperations(state).move_character(tool.actor, tool.destination)


def _resolve_wait(tool: Wait, state: WorldState) -> str:
    char = state.characters.get(tool.actor)
    location = char.location if char else ""
    text = f"{tool.actor} waits."
    state.history.append(HistoryEvent(text=text, location=location, characters=[tool.actor]))
    return text


def _resolve_attack(tool: Attack, state: WorldState) -> str:
    return WorldOperations(state).attack(tool.actor, tool.target)


def _resolve_create(tool: Create, state: WorldState) -> str:
    ops = WorldOperations(state)
    if tool.type == "location":
        connections = [tool.location] if tool.location else []
        return ops.add_location(slugify(tool.name), description=tool.description, connections=connections)
    if tool.type == "item":
        if not tool.location:
            return "Cannot create item — location is required."
        return ops.create_item(tool.name, tool.location)
    if tool.type == "npc":
        if not tool.location:
            return "Cannot create NPC — location is required."
        return ops.spawn_character(
            slugify(tool.name),
            role=tool.role or "",
            location_id=tool.location,
            backstory=tool.description,
            goal=tool.goal or "",
        )
    if tool.type == "quest":
        return ops.add_quest(
            slugify(tool.name),
            title=tool.name,
            description=tool.description,
            owner=tool.owner,
            plan=tool.plan,
        )
    return f"Unknown create type: {tool.type!r}."


def _resolve_modify(tool: Modify, state: WorldState) -> str:
    ops = WorldOperations(state)
    if tool.action == "update_quest":
        if not tool.status and not tool.step and not tool.advance:
            return "Cannot update a quest without status, step, or advance."
        return ops.advance_quest(tool.target_id, new_status=tool.status, step=tool.step, advance=tool.advance)
    if tool.action == "remove_npc":
        return ops.delete_npc(tool.target_id, reason=tool.reason or "")
    if tool.action == "update_location":
        return ops.modify_location(tool.target_id, description=tool.reason)
    return f"Unknown modify action: {tool.action!r}."


async def _resolve_action(tool: Action, state: WorldState, usage: RunUsage | None, logger: Logger | None) -> str:
    char = state.characters.get(tool.actor)
    if not char:
        return f"Cannot resolve action — character {tool.actor!r} not found."
    prompt = f"Resolve this action: {tool.description}"
    if tool.target:
        prompt += f" (target: {tool.target})"
    deps = _ActionResolverDeps(char=char, state=state, description=tool.description, target=tool.target)
    if logger:
        with logger.run("action_resolver"):
            result = await _action_agent.run(prompt, deps=deps, usage=usage)
            logger.log_messages("action_resolver", result.all_messages())
    else:
        result = await _action_agent.run(prompt, deps=deps, usage=usage)
    return result.output


# ============================================================
# Internal LLM sub-agent for free-form Action tool
# ============================================================

@dataclass
class _ActionResolverDeps:
    char: Character
    state: WorldState
    description: str
    target: str | None = None


# Keep public alias for context.py / tests that still reference the old name.
ActionResolverDeps = _ActionResolverDeps


_action_agent: Agent[_ActionResolverDeps, str] = Agent(
    model=create_model(),
    deps_type=_ActionResolverDeps,
    output_type=ToolOutput(str, name="done"),
    instructions="Resolve exactly one character action into concrete state changes. Report the outcome in one short, plain sentence — no scene-setting or flourishes.",
)

# Public alias for tests / external imports.
agent = _action_agent


@_action_agent.system_prompt
def _identity(_: RunContext[_ActionResolverDeps]) -> str:
    return action_resolver_system()


@_action_agent.instructions
def _context(ctx: RunContext[_ActionResolverDeps]) -> str:
    return action_resolver_context(
        ctx.deps.char,
        ctx.deps.state,
        description=ctx.deps.description,
        target=ctx.deps.target,
    )


def _ops(ctx: RunContext[_ActionResolverDeps]) -> WorldOperations:
    return WorldOperations(ctx.deps.state)


@_action_agent.tool
def remember(
    ctx: RunContext[_ActionResolverDeps],
    knowledge: str,
    character_id: str | None = None,
) -> str:
    """add a concrete piece of knowledge to the acting character or another known character."""
    return _ops(ctx).add_knowledge(character_id or ctx.deps.char.id, knowledge)


@_action_agent.tool
def add_detail(
    ctx: RunContext[_ActionResolverDeps],
    detail: str,
    location: str | None = None,
) -> str:
    """add a newly discovered concrete detail to the current location or another known location."""
    return _ops(ctx).modify_location(location or ctx.deps.char.location, add_feature=detail)


@_action_agent.tool
def discover_exit(
    ctx: RunContext[_ActionResolverDeps],
    name: str,
    description: str,
    location_id: str | None = None,
    anchor_location: str | None = None,
) -> str:
    """add a newly discovered reachable location and connect it to the current place."""
    anchor = anchor_location or ctx.deps.char.location
    return _ops(ctx).add_location(location_id or slugify(name), description=description, connections=[anchor])


@_action_agent.tool
def adjust_hp(
    ctx: RunContext[_ActionResolverDeps],
    delta: int,
    character_id: str | None = None,
    reason: str | None = None,
) -> str:
    """change a character's HP by a small signed amount when the action causes harm or recovery."""
    target = character_id or ctx.deps.char.id
    ops = _ops(ctx)
    return ops.heal(target, delta) if delta >= 0 else ops.damage(target, -delta)


@_action_agent.tool
def update_quest(
    ctx: RunContext[_ActionResolverDeps],
    quest_id: str,
    status: str,
) -> str:
    """update a quest status when the action clearly advances or completes it."""
    return _ops(ctx).advance_quest(quest_id, new_status=status)


@_action_agent.tool
def take(
    ctx: RunContext[_ActionResolverDeps],
    item_name: str,
    character_id: str | None = None,
) -> str:
    """move an item from a location into a character's inventory."""
    return _ops(ctx).take_item(character_id or ctx.deps.char.id, item_name)


@_action_agent.tool
def drop(
    ctx: RunContext[_ActionResolverDeps],
    item_name: str,
    character_id: str | None = None,
) -> str:
    """move an item from a character's inventory into a location."""
    return _ops(ctx).drop_item(character_id or ctx.deps.char.id, item_name)


@_action_agent.tool
def create_item(
    ctx: RunContext[_ActionResolverDeps],
    item_name: str,
    location: str | None = None,
) -> str:
    """place a new item in a location. use when the action reveals or produces a tangible object."""
    return _ops(ctx).create_item(item_name, location or ctx.deps.char.location)


@_action_agent.tool
def give_gold(ctx: RunContext[_ActionResolverDeps], amount: int, character_id: str) -> str:
    """give some of my gold to another character — payment, bribe, tip. no item involved."""
    return _ops(ctx).give_gold(ctx.deps.char.id, character_id, amount)


@_action_agent.tool
def trade_item(
    ctx: RunContext[_ActionResolverDeps],
    item_name: str,
    price: int,
    counterparty_id: str,
    role: Literal["buyer", "seller"] = "buyer",
) -> str:
    """exchange an item for gold with another character here. role='buyer': I pay for their item. role='seller': they pay for mine."""
    me = ctx.deps.char.id
    buyer, seller = (me, counterparty_id) if role == "buyer" else (counterparty_id, me)
    return _ops(ctx).trade_item(buyer, seller, item_name, price)


@_action_agent.tool
def create_npc(
    ctx: RunContext[_ActionResolverDeps],
    name: str,
    role: str = "",
    goal: str = "",
    backstory: str = "",
    location: str | None = None,
) -> str:
    """add a new NPC to the world. use when the action reveals or encounters a new character."""
    return _ops(ctx).spawn_character(
        slugify(name),
        role=role,
        location_id=location or ctx.deps.char.location,
        backstory=backstory,
        goal=goal,
    )

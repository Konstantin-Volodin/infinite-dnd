"""Game loop. Each tick: one actor takes a turn → resolve → stamp elapsed time → enrich world → review quests."""

import asyncio

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from src.engine.state import StateManager, WorldState
from src.engine.state.models import HistoryEvent
from src.agents.character.agent import CharacterDeps, agent as character_agent
from src.agents.character.tools import Action, CharacterTool, Speak, Travel, Wait
from src.agents.quest_reviewer.agent import QuestReviewerDeps, agent as quest_reviewer_agent
from src.agents.quest_reviewer.tools import Modify
from src.agents.time_keeper.agent import TimeKeeperDeps, agent as time_keeper_agent
from src.agents.world_builder.agent import WorldBuilderDeps, agent as world_builder_agent
from src.agents.world_builder.tools import Create
from src.agents.action_resolver.agent import resolve
from src.interface.logger import Logger


_AGENT_USAGE = UsageLimits(request_limit=12)
_QUEST_USAGE = UsageLimits(request_limit=6)
_TIME_USAGE = UsageLimits(request_limit=6)
_ENRICH_USAGE = UsageLimits(request_limit=8)

# Locations must resolve before NPCs/items that anchor to them. Quests last (anchor to PCs).
_CREATE_ORDER = {"location": 0, "npc": 1, "item": 2, "quest": 3}


# ─── Scheduler ────────────────────────────────────────────────

def _scene_actors(state: WorldState, active_pc_id: str) -> list[str]:
    """Characters present in the active PC's current location. PC first, then others by id."""
    scene = state.characters[active_pc_id].location
    present = [cid for cid, c in state.characters.items() if c.location == scene]
    present.sort(key=lambda cid: (cid != active_pc_id, cid))
    return present


def _pick_next_actor(state: WorldState, active_pc_id: str, tick: int) -> str:
    actors = _scene_actors(state, active_pc_id)
    return actors[tick % len(actors)]


def _format_clock(total_minutes: int) -> str:
    day = total_minutes // 1440 + 1
    remainder = total_minutes % 1440
    return f"day {day}, {remainder // 60:02d}:{remainder % 60:02d}"


def _describe_tool(tool: CharacterTool) -> str:
    """One-line preview of the acting character's chosen step."""
    if isinstance(tool, Speak):
        head = f"speak → {tool.target}" if tool.target else "speak"
        return f'{head}: "{tool.message}"'
    if isinstance(tool, Travel):
        return f"travel → {tool.destination}"
    if isinstance(tool, Wait):
        return "wait"
    if isinstance(tool, Action):
        suffix = f" ({tool.target})" if tool.target else ""
        return f"action{suffix}: {tool.description}"
    return repr(tool)


# ─── Agent flows ──────────────────────────────────────────────

async def flow_agent_turn(actor_id: str, state: WorldState, logger: Logger) -> CharacterTool | None:
    """Ask the acting character to pick one next step."""
    char = state.characters[actor_id]
    print(f"  [{actor_id}]", flush=True)
    label = f"character:{actor_id}"
    try:
        with logger.run(label):
            result = await character_agent.run(
                "Choose exactly ONE next step by calling action, speak, travel, or wait.",
                deps=CharacterDeps(char=char, state=state),
                usage_limits=_AGENT_USAGE,
            )
    except UsageLimitExceeded as exc:
        print(f"  [limit] {actor_id}'s turn ended: {exc}", flush=True)
        return None
    logger.log_messages(label, result.all_messages())
    return result.output


async def flow_world_enrich(state: WorldState, logger: Logger) -> list[Create]:
    """Materialize entities revealed by recent events (locations before NPCs/items)."""
    label = "world_builder"
    try:
        with logger.run(label):
            result = await world_builder_agent.run(
                "Register any new entities revealed by the recent events. Return an empty list if nothing new.",
                deps=WorldBuilderDeps(state=state),
                usage_limits=_ENRICH_USAGE,
            )
    except UsageLimitExceeded as exc:
        print(f"  [limit] world enrichment ended: {exc}", flush=True)
        return []
    logger.log_messages(label, result.all_messages())
    intents = result.output or []
    if intents:
        print(f"  [world] {len(intents)} new entities revealed")
    return sorted(intents, key=lambda i: _CREATE_ORDER.get(i.type, 3))


async def flow_quest_review(state: WorldState, logger: Logger) -> list[Modify]:
    """Advance quests against recent events. Structural — never narrates."""
    if not any(q.status.lower() not in {"completed", "failed"} for q in state.quests.values()):
        return []
    label = "quest_reviewer"
    try:
        with logger.run(label):
            result = await quest_reviewer_agent.run(
                "Review active quests against recent events. Call review with any progress, or an empty list.",
                deps=QuestReviewerDeps(state=state),
                usage_limits=_QUEST_USAGE,
            )
    except UsageLimitExceeded as exc:
        print(f"  [limit] quest review ended: {exc}", flush=True)
        return []
    logger.log_messages(label, result.all_messages())
    return result.output or []


async def flow_time_review(event_texts: list[str], logger: Logger) -> list[int]:
    """One minute-estimate per event, in order. Falls back to 1m per event on limit."""
    if not event_texts:
        return []
    label = "time_keeper"
    try:
        with logger.run(label):
            result = await time_keeper_agent.run(
                "Estimate minutes elapsed for each event. Return exactly one integer per event, in order.",
                deps=TimeKeeperDeps(events=event_texts),
                usage_limits=_TIME_USAGE,
            )
    except UsageLimitExceeded as exc:
        print(f"  [limit] time review ended: {exc}", flush=True)
        return [1] * len(event_texts)
    logger.log_messages(label, result.all_messages())
    return result.output or []


# ─── Tick composition ────────────────────────────────────────

async def _stamp_time(new_events: list[HistoryEvent], state: WorldState, logger: Logger) -> None:
    """Annotate each new event with estimated minutes and advance the world clock."""
    if not new_events:
        return
    minutes = await flow_time_review([e.text for e in new_events], logger)
    if len(minutes) != len(new_events):
        minutes = [1] * len(new_events)
    for event, mins in zip(new_events, minutes):
        event.minutes_elapsed = mins
    state.minutes_elapsed += sum(minutes)

    for event in new_events:
        print(f"  {event.text}  (+{event.minutes_elapsed}m)")
    print(f"  [clock: {_format_clock(state.minutes_elapsed)}]")


async def tick(active_pc_id: str, state: WorldState, tick_index: int, logger: Logger) -> None:
    actor_id = _pick_next_actor(state, active_pc_id, tick_index)

    intent = await flow_agent_turn(actor_id, state, logger)
    if intent is None:
        return
    print(f"    ↳ {_describe_tool(intent)}")

    # 1. Resolve the turn and stamp elapsed time onto the resulting events.
    pre = len(state.history)
    await resolve(intent, state, logger=logger)
    await _stamp_time(state.history[pre:], state, logger)

    # 2. Enrich the world. Revealed entities are retcons — logged but not time-stamped.
    pre_enrich = len(state.history)
    for create_intent in await flow_world_enrich(state, logger):
        await resolve(create_intent, state, logger=logger)
    for event in state.history[pre_enrich:]:
        print(f"  {event.text}  (revealed)")

    # 3. Review quests. Step-level progress; may append XP events via advance_quest.
    pre_quest = len(state.history)
    for update in await flow_quest_review(state, logger):
        msg = await resolve(update, state, logger=logger)
        print(f"  [quest] {update.target_id}: {msg}")
    for event in state.history[pre_quest:]:
        print(f"  {event.text}")


# ============================================================
# Entry point
# ============================================================

def _snapshot(state: WorldState) -> dict:
    """World/quest/xp counters for scorecard.py — logged before and after every tick."""
    quests = state.quests.values()
    return {
        "quests_active": sum(1 for q in quests if q.status.lower() not in {"completed", "failed"}),
        "quests_completed": sum(1 for q in quests if q.status.lower() == "completed"),
        "quests_failed": sum(1 for q in quests if q.status.lower() == "failed"),
        "locations": len(state.locations),
        "characters": len(state.characters),
        "total_xp": sum(c.stats.xp for c in state.characters.values()),
        "minutes_elapsed": state.minutes_elapsed,
    }


async def _run_game(scenario: str | None, character_id: str | None, max_turns: int) -> None:
    manager = StateManager(scenario=scenario)
    state = manager.init_state()

    pc_id = character_id or manager.manifest["pc"]
    if pc_id not in state.characters:
        raise RuntimeError(f"PC '{pc_id}' not in scenario '{manager.scenario}'")

    print(f"\n=== {manager.manifest.get('title', manager.scenario)} ===")
    print(manager.manifest.get("hook", ""))
    print(f"Playing as: {pc_id}\n")

    logger = Logger(character_id=pc_id, max_turns=max_turns)
    try:
        logger.log_event("world_snapshot", **_snapshot(state))
        for t in range(max_turns):
            print(f"\n--- Tick {t + 1} ---")
            logger.log_turn(t + 1)
            await tick(pc_id, state, t, logger)
            logger.log_event("world_snapshot", **_snapshot(state))
            state.time += 1
            manager.save_state(state)
    finally:
        logger.close()


def run_game(character_id: str | None = None, max_turns: int = 50, scenario: str | None = None) -> None:
    asyncio.run(_run_game(scenario, character_id, max_turns))

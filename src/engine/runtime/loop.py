"""Game loop. Each tick: one actor takes a turn → resolve → stamp elapsed time → enrich world → review quests."""

import asyncio
import sys
from collections.abc import Awaitable, Callable

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from src.engine.state import StateManager, WorldOperations, WorldState
from src.engine.state.models import HistoryEvent
from src.agents.character.agent import CharacterDeps, agent as character_agent
from src.agents.character.tools import Action, Attack, CharacterTool, Speak, Travel, Wait
from src.agents.dm.agent import DMDeps, DMResult, agent as dm_agent
from src.agents.action_resolver.agent import resolve
from src.interface.session_log import Logger


_AGENT_USAGE = UsageLimits(request_limit=12)
_DM_USAGE = UsageLimits(request_limit=16)

# Locations must resolve before NPCs/items that anchor to them. Quests last (anchor to PCs).
_CREATE_ORDER = {"location": 0, "npc": 1, "item": 2, "quest": 3}


# ─── Scheduler ────────────────────────────────────────────────

def _scene_actors(state: WorldState, active_pc_id: str) -> list[str]:
    """Living characters present in the active PC's current location. PC first, then others by id."""
    scene = state.characters[active_pc_id].location
    present = [cid for cid, c in state.characters.items() if c.location == scene and c.stats.hp > 0]
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
    if isinstance(tool, Attack):
        return f"attack → {tool.target}"
    if isinstance(tool, Action):
        suffix = f" ({tool.target})" if tool.target else ""
        return f"action{suffix}: {tool.description}"
    return repr(tool)


# ─── Agent flows ──────────────────────────────────────────────

async def flow_agent_turn(
    actor_id: str,
    state: WorldState,
    logger: Logger,
    pc_controller: Callable[[str, WorldState], Awaitable[CharacterTool]] | None = None,
) -> CharacterTool | None:
    """Ask the acting character to pick one next step."""
    char = state.characters[actor_id]
    print(f"  [{actor_id}]", flush=True)
    if pc_controller is not None:
        intent = await pc_controller(actor_id, state)
        logger.log_event("player_action", actor=actor_id, tool=intent.kind, action=intent.model_dump(mode="json"))
        return intent
    label = f"character:{actor_id}"
    try:
        with logger.run(label):
            result = await character_agent.run(
                "Choose exactly ONE next step by calling action, speak, travel, attack, or wait.",
                deps=CharacterDeps(char=char, state=state),
                usage_limits=_AGENT_USAGE,
            )
            logger.log_messages(label, result.all_messages())
    except UsageLimitExceeded as exc:
        print(f"  [limit] {actor_id}'s turn ended: {exc}", flush=True)
        return None
    return result.output


async def flow_dm(state: WorldState, new_events: list[HistoryEvent], logger: Logger) -> DMResult:
    """One LLM call: enrich the world, review quests, and estimate time for this tick's new events."""
    if not new_events:
        return DMResult(creates=[], modifies=[], minutes=[])
    new_texts = [e.text for e in new_events]
    tail = state.history[: -len(new_events)]  # new_events is non-empty here (checked above)
    context_events = [e.text for e in tail[-10:]]
    label = "dm"
    try:
        with logger.run(label):
            result = await dm_agent.run(
                "Register any new entities, report quest progress, and estimate minutes elapsed for each new event.",
                deps=DMDeps(state=state, context_events=context_events, new_events=new_texts),
                usage_limits=_DM_USAGE,
            )
            logger.log_messages(label, result.all_messages())
    except UsageLimitExceeded as exc:
        print(f"  [limit] dm review ended: {exc}", flush=True)
        return DMResult(creates=[], modifies=[], minutes=[1] * len(new_events))
    dm_result = result.output
    if not dm_result.minutes or len(dm_result.minutes) != len(new_events):
        dm_result.minutes = [1] * len(new_events)
    dm_result.creates = sorted(dm_result.creates, key=lambda i: _CREATE_ORDER.get(i.type, 3))
    return dm_result


# ─── Tick composition ────────────────────────────────────────

async def tick(
    active_pc_id: str,
    state: WorldState,
    tick_index: int,
    logger: Logger,
    pc_controller: Callable[[str, WorldState], Awaitable[CharacterTool]] | None = None,
) -> None:
    actor_id = _pick_next_actor(state, active_pc_id, tick_index)

    controller = pc_controller if actor_id == active_pc_id else None
    intent = await flow_agent_turn(actor_id, state, logger, controller)
    if intent is None:
        return
    print(f"    ↳ {_describe_tool(intent)}")

    # 1. Resolve the turn.
    pre = len(state.history)
    await resolve(intent, state, logger=logger)
    new_events = state.history[pre:]

    # 2. One DM call: time estimates, new entities, and quest progress.
    dm = await flow_dm(state, new_events, logger)

    # 2a. Stamp elapsed time onto the resulting events and advance the clock.
    for event, mins in zip(new_events, dm.minutes):
        event.minutes_elapsed = mins
    state.minutes_elapsed += sum(dm.minutes)
    for event in new_events:
        print(f"  {event.text}  (+{event.minutes_elapsed}m)")
    if new_events:
        print(f"  [clock: {_format_clock(state.minutes_elapsed)}]")

    # 2b. Enrich the world. Revealed entities are retcons — logged but not time-stamped.
    pre_enrich = len(state.history)
    for create_intent in dm.creates:
        await resolve(create_intent, state, logger=logger)
    for event in state.history[pre_enrich:]:
        print(f"  {event.text}  (revealed)")

    # 2c. Review quests. Step-level progress; may append XP events via advance_quest.
    pre_quest = len(state.history)
    for update in dm.modifies:
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


async def _run_game(
    scenario: str | None,
    character_id: str | None,
    max_turns: int,
    new_character: dict | None,
    *,
    resume: bool = False,
    stop_check: Callable[[], bool] | None = None,
    pc_controller: Callable[[str, WorldState], Awaitable[CharacterTool]] | None = None,
    progress_callback: Callable[[WorldState], None] | None = None,
) -> None:
    manager = StateManager(scenario=scenario)
    latest = manager.latest_snapshot_name() if resume else None
    state = manager.load_state(latest) if latest else manager.init_state()

    if new_character:
        result = WorldOperations(state).spawn_character(**new_character)
        print(result)
        if result.startswith("Cannot spawn"):
            raise RuntimeError(result)
        pc_id = new_character["character_id"]
    else:
        pc_id = character_id or manager.manifest["pc"]
        if pc_id not in state.characters:
            raise RuntimeError(f"PC '{pc_id}' not in scenario '{manager.scenario}'")

    print(f"\n=== {manager.manifest.get('title', manager.scenario)} ===")
    print(manager.manifest.get("hook", ""))
    print(f"Playing as: {pc_id}\n")

    logger = Logger(
        character_id=pc_id,
        max_turns=max_turns,
        scenario=manager.scenario,
        scenario_title=manager.manifest.get("title", manager.scenario),
    )
    try:
        manager.save_state(state)
        if progress_callback:
            progress_callback(state)
        logger.log_event("world_snapshot", **_snapshot(state))
        for t in range(max_turns):
            if stop_check and stop_check():
                logger.log_event("run_stopped")
                break
            if state.characters[pc_id].stats.hp <= 0:
                print(f"\n=== {pc_id} has died. The campaign ends. ===")
                logger.log_event("pc_death", pc=pc_id)
                break
            print(f"\n--- Tick {state.time + 1} ---")
            logger.log_turn(t + 1)
            await tick(pc_id, state, state.time, logger, pc_controller)
            logger.log_event("world_snapshot", **_snapshot(state))
            state.time += 1
            manager.save_state(state)
            if progress_callback:
                progress_callback(state)
    finally:
        logger.close()


def run_game(character_id: str | None = None, max_turns: int = 50, scenario: str | None = None, new_character: dict | None = None) -> None:
    # Narrative text (arrows, em-dashes) doesn't fit Windows' default console codepage.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run_game(scenario, character_id, max_turns, new_character))

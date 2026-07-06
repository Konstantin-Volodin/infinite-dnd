"""Game loop. Each tick: one actor takes a turn → resolve → stamp elapsed time → enrich world → review quests."""

import asyncio
import sys
from collections.abc import Awaitable, Callable
from datetime import datetime
from io import TextIOWrapper

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from src.engine.state import StateManager, WorldOperations, WorldState
from src.engine.state.models import HistoryEvent
from src.agents.character.agent import CharacterDeps, agent as character_agent
from src.agents.character.tools import Action, Attack, CharacterTool, Check, Speak, Travel, Wait
from src.agents.dm.agent import DMDeps, DMResult, agent as dm_agent
from src.agents.dm.director import DirectorDeps, agent as director_agent
from src.agents.action_resolver.agent import resolve
from src.interface.session_log import Logger
from .chronicle import compact_history
from .replay import ReplayTape


_AGENT_USAGE = UsageLimits(request_limit=12)
_DM_USAGE = UsageLimits(request_limit=16)

# Locations must resolve before NPCs/items that anchor to them. Quests last (anchor to PCs).
_CREATE_ORDER = {"location": 0, "npc": 1, "item": 2, "quest": 3}

# Stall detection — director fires when no quest advanced for this many ticks,
# or the last few events are all talk/waiting.
_STALL_QUIET_TICKS = 6
_STALL_IDLE_EVENTS = 5


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
    if isinstance(tool, Check):
        target = f" vs {tool.opponent}" if tool.opponent else f" vs DC {tool.difficulty}"
        return f"check ({tool.ability}{target}): {tool.description}"
    if isinstance(tool, Action):
        suffix = f" ({tool.target})" if tool.target else ""
        return f"action{suffix}: {tool.description}"
    return repr(tool)


# ─── Stall detection ──────────────────────────────────────────

def _is_idle_event(text: str) -> bool:
    """Speak/wait-style event — mirrors the dialogue heuristic in character/context.py."""
    lowered = text.lower()
    return '"' in text or "says" in lowered or "waits" in lowered


def _is_stalled(state: WorldState) -> bool:
    """True when no quest has advanced for a while, or recent events are all chatter/waiting."""
    if state.time - state.last_quest_advance_time >= _STALL_QUIET_TICKS:
        return True
    tail = state.history[-_STALL_IDLE_EVENTS:]
    return len(tail) == _STALL_IDLE_EVENTS and all(_is_idle_event(e.text) for e in tail)


def _record_intervention(state: WorldState, quest_id: str | None) -> str:
    """Bump the escalation counter for the targeted quest, or 'world' if untargeted/unknown."""
    key = quest_id if quest_id and quest_id in state.quests else "world"
    state.director_interventions[key] = state.director_interventions.get(key, 0) + 1
    return key


# ─── Agent flows ──────────────────────────────────────────────

async def flow_agent_turn(
    actor_id: str,
    state: WorldState,
    logger: Logger,
    pc_controller: Callable[[str, WorldState], Awaitable[CharacterTool]] | None = None,
    replay: ReplayTape | None = None,
) -> CharacterTool | None:
    """Ask the acting character to pick one next step."""
    char = state.characters[actor_id]
    print(f"  [{actor_id}]", flush=True)
    if replay and replay.is_playback:
        return replay.character(actor_id)
    if pc_controller is not None:
        intent = await pc_controller(actor_id, state)
        logger.log_event("player_action", actor=actor_id, tool=intent.kind, action=intent.model_dump(mode="json"))
        return replay.character(actor_id, intent) if replay else intent
    label = f"character:{actor_id}"
    try:
        with logger.run(label):
            result = await character_agent.run(
                "Choose exactly ONE next step by calling action, check, speak, travel, attack, or wait.",
                deps=CharacterDeps(char=char, state=state),
                usage_limits=_AGENT_USAGE,
            )
            logger.log_messages(label, result.all_messages())
    except UsageLimitExceeded as exc:
        print(f"  [limit] {actor_id}'s turn ended: {exc}", flush=True)
        return replay.character(actor_id, None) if replay else None
    output = result.output
    return replay.character(actor_id, output) if replay else output


async def flow_dm(
    state: WorldState, new_events: list[HistoryEvent], logger: Logger, replay: ReplayTape | None = None
) -> DMResult:
    """One LLM call: enrich the world, review quests, and estimate time for this tick's new events."""
    if not new_events:
        return DMResult(creates=[], modifies=[], minutes=[])
    if replay and replay.is_playback:
        return replay.dm()
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
        fallback = DMResult(creates=[], modifies=[], minutes=[1] * len(new_events))
        return replay.dm(fallback) if replay else fallback
    dm_result = result.output
    if not dm_result.minutes or len(dm_result.minutes) != len(new_events):
        dm_result.minutes = [1] * len(new_events)
    dm_result.creates = sorted(dm_result.creates, key=lambda i: _CREATE_ORDER.get(i.type, 3))
    return replay.dm(dm_result) if replay else dm_result


async def flow_director(
    state: WorldState, location_id: str, logger: Logger, replay: ReplayTape | None = None
) -> None:
    """Stall-breaker: one LLM call that introduces a single complication grounded in existing state."""
    label = "director"
    if replay and replay.is_playback:
        beat = replay.director()
    else:
        try:
            with logger.run(label):
                result = await director_agent.run(
                    "The story has stalled. Introduce exactly one grounded complication.",
                    deps=DirectorDeps(state=state, location_id=location_id),
                    usage_limits=_DM_USAGE,
                )
                logger.log_messages(label, result.all_messages())
        except UsageLimitExceeded as exc:
            print(f"  [limit] director beat ended: {exc}", flush=True)
            if replay:
                replay.director(None)
            return
        beat = result.output
        if replay:
            beat = replay.director(beat)

    if beat is None:
        return

    # Director events are retcon-style arrivals: logged, printed, 0 minutes.
    pre = len(state.history)
    if beat.create:
        await resolve(beat.create, state, logger=logger)
    if beat.event:
        WorldOperations(state).world_event(beat.event, location_id)
    for event in state.history[pre:]:
        print(f"  {event.text}  (director)")

    key = _record_intervention(state, beat.quest_id)
    logger.log_event("director_beat", quest=key, text=beat.event)


# ─── Tick composition ────────────────────────────────────────

async def tick(
    active_pc_id: str,
    state: WorldState,
    tick_index: int,
    logger: Logger,
    pc_controller: Callable[[str, WorldState], Awaitable[CharacterTool]] | None = None,
    replay: ReplayTape | None = None,
) -> None:
    actor_id = _pick_next_actor(state, active_pc_id, tick_index)

    controller = pc_controller if actor_id == active_pc_id else None
    intent = await flow_agent_turn(actor_id, state, logger, controller, replay)
    if intent is None:
        return
    print(f"    ↳ {_describe_tool(intent)}")

    # 1. Resolve the turn.
    pre = len(state.history)
    if replay and replay.is_playback and isinstance(intent, (Action, Check)):
        replay.action_resolution(actor_id, state)
    else:
        resolution = await resolve(intent, state, logger=logger)
        if replay and isinstance(intent, (Action, Check)):
            replay.action_resolution(actor_id, state, resolution)
    new_events = state.history[pre:]

    # 2. One DM call: time estimates, new entities, and quest progress.
    dm = await flow_dm(state, new_events, logger, replay)

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

    # 3. Director beat: when the story stalls, one proactive complication breaks it.
    if _is_stalled(state):
        await flow_director(state, state.characters[active_pc_id].location, logger, replay)
        state.last_quest_advance_time = state.time  # suppress consecutive fires


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
    replay: ReplayTape | None = None,
) -> None:
    if replay:
        scenario, character_id = replay.resolve_context(scenario, character_id)
    session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    manager = StateManager(scenario=scenario, run_id=None if resume else session_id, resume=resume)
    session_id = manager.run_id
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

    if replay:
        replay.bind_context(manager.scenario, pc_id)

    print(f"\n=== {manager.manifest.get('title', manager.scenario)} ===")
    print(manager.manifest.get("hook", ""))
    print(f"Playing as: {pc_id}\n")

    logger = Logger(
        character_id=pc_id,
        max_turns=max_turns,
        scenario=manager.scenario,
        scenario_title=manager.manifest.get("title", manager.scenario),
        session_id=session_id,
        append=resume,
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
            await tick(pc_id, state, state.time, logger, pc_controller, replay)
            await compact_history(state, logger, replay)  # between ticks only — never mid-tick
            logger.log_event("world_snapshot", **_snapshot(state))
            state.time += 1
            manager.save_state(state)
            if progress_callback:
                progress_callback(state)
    finally:
        logger.close()
    if replay:
        replay.assert_consumed()


def run_game(
    character_id: str | None = None,
    max_turns: int = 50,
    scenario: str | None = None,
    new_character: dict | None = None,
    *,
    replay: ReplayTape | None = None,
    pc_controller: Callable[[str, WorldState], Awaitable[CharacterTool]] | None = None,
) -> None:
    # Narrative text (arrows, em-dashes) doesn't fit Windows' default console codepage.
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run_game(scenario, character_id, max_turns, new_character, replay=replay, pc_controller=pc_controller))

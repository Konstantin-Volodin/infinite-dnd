"""Game loop. Each tick: one actor takes a turn → resolve → stamp elapsed time → enrich world → review quests."""

import asyncio

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from src.engine.state import StateManager, WorldState
from src.engine.state.models import HistoryEvent
from src.agents.character.agent import CharacterDeps, agent as character_agent
from src.agents.quest_reviewer.agent import QuestReviewerDeps, agent as quest_reviewer_agent
from src.agents.time_keeper.agent import TimeKeeperDeps, agent as time_keeper_agent
from src.agents.world_builder.agent import WorldBuilderDeps, agent as world_builder_agent
from src.agents.action_resolver.agent import resolve
from src.agents.intents import (
    ActionIntent,
    CharacterIntent,
    CreateIntent,
    ModifyIntent,
    SpeakIntent,
    TravelIntent,
    WaitIntent,
)


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


def _describe_intent(intent: CharacterIntent) -> str:
    """One-line preview of the acting character's chosen step."""
    if isinstance(intent, SpeakIntent):
        head = f"speak → {intent.target}" if intent.target else "speak"
        return f'{head}: "{intent.message}"'
    if isinstance(intent, TravelIntent):
        return f"travel → {intent.destination}"
    if isinstance(intent, WaitIntent):
        return "wait"
    if isinstance(intent, ActionIntent):
        suffix = f" ({intent.target})" if intent.target else ""
        return f"action{suffix}: {intent.description}"
    return repr(intent)


# ─── Agent flows ──────────────────────────────────────────────

async def flow_agent_turn(actor_id: str, state: WorldState) -> CharacterIntent | None:
    """Ask the acting character to pick one next step."""
    char = state.characters[actor_id]
    print(f"  [{actor_id}]", flush=True)
    try:
        result = await character_agent.run(
            "Choose exactly ONE next step by calling action, speak, travel, or wait.",
            deps=CharacterDeps(char=char, state=state),
            usage_limits=_AGENT_USAGE,
        )
    except UsageLimitExceeded as exc:
        print(f"  [limit] {actor_id}'s turn ended: {exc}", flush=True)
        return None
    return result.output


async def flow_world_enrich(state: WorldState) -> list[CreateIntent]:
    """Materialize entities revealed by recent events (locations before NPCs/items)."""
    try:
        result = await world_builder_agent.run(
            "Register any new entities revealed by the recent events. Return an empty list if nothing new.",
            deps=WorldBuilderDeps(state=state),
            usage_limits=_ENRICH_USAGE,
        )
    except UsageLimitExceeded as exc:
        print(f"  [limit] world enrichment ended: {exc}", flush=True)
        return []
    intents = result.output or []
    if intents:
        print(f"  [world] {len(intents)} new entities revealed")
    return sorted(intents, key=lambda i: _CREATE_ORDER.get(i.type, 3))


async def flow_quest_review(state: WorldState) -> list[ModifyIntent]:
    """Advance quests against recent events. Structural — never narrates."""
    if not any(q.status.lower() not in {"completed", "failed"} for q in state.quests.values()):
        return []
    try:
        result = await quest_reviewer_agent.run(
            "Review active quests against recent events. Call review with any progress, or an empty list.",
            deps=QuestReviewerDeps(state=state),
            usage_limits=_QUEST_USAGE,
        )
    except UsageLimitExceeded as exc:
        print(f"  [limit] quest review ended: {exc}", flush=True)
        return []
    return result.output or []


async def flow_time_review(event_texts: list[str]) -> list[int]:
    """One minute-estimate per event, in order. Falls back to 1m per event on limit."""
    if not event_texts:
        return []
    try:
        result = await time_keeper_agent.run(
            "Estimate minutes elapsed for each event. Return exactly one integer per event, in order.",
            deps=TimeKeeperDeps(events=event_texts),
            usage_limits=_TIME_USAGE,
        )
    except UsageLimitExceeded as exc:
        print(f"  [limit] time review ended: {exc}", flush=True)
        return [1] * len(event_texts)
    return result.output or []


# ─── Tick composition ────────────────────────────────────────

async def _stamp_time(new_events: list[HistoryEvent], state: WorldState) -> None:
    """Annotate each new event with estimated minutes and advance the world clock."""
    if not new_events:
        return
    minutes = await flow_time_review([e.text for e in new_events])
    if len(minutes) != len(new_events):
        minutes = [1] * len(new_events)
    for event, mins in zip(new_events, minutes):
        event.minutes_elapsed = mins
    state.minutes_elapsed += sum(minutes)

    for event in new_events:
        print(f"  {event.text}  (+{event.minutes_elapsed}m)")
    print(f"  [clock: {_format_clock(state.minutes_elapsed)}]")


async def tick(active_pc_id: str, state: WorldState, tick_index: int) -> None:
    actor_id = _pick_next_actor(state, active_pc_id, tick_index)

    intent = await flow_agent_turn(actor_id, state)
    if intent is None:
        return
    print(f"    ↳ {_describe_intent(intent)}")

    # 1. Resolve the turn and stamp elapsed time onto the resulting events.
    pre = len(state.history)
    await resolve(intent, state)
    await _stamp_time(state.history[pre:], state)

    # 2. Enrich the world. Revealed entities are retcons — logged but not time-stamped.
    pre_enrich = len(state.history)
    for create_intent in await flow_world_enrich(state):
        await resolve(create_intent, state)
    for event in state.history[pre_enrich:]:
        print(f"  {event.text}  (revealed)")

    # 3. Review quests. Step-level progress; may append XP events via advance_quest.
    pre_quest = len(state.history)
    for update in await flow_quest_review(state):
        msg = await resolve(update, state)
        print(f"  [quest] {update.target_id}: {msg}")
    for event in state.history[pre_quest:]:
        print(f"  {event.text}")


# ============================================================
# Entry point
# ============================================================

async def _run_game(scenario: str | None, character_id: str | None, max_turns: int) -> None:
    manager = StateManager(scenario=scenario)
    state = manager.init_state()

    pc_id = character_id or manager.manifest["pc"]
    if pc_id not in state.characters:
        raise RuntimeError(f"PC '{pc_id}' not in scenario '{manager.scenario}'")

    print(f"\n=== {manager.manifest.get('title', manager.scenario)} ===")
    print(manager.manifest.get("hook", ""))
    print(f"Playing as: {pc_id}\n")

    for t in range(max_turns):
        print(f"\n--- Tick {t + 1} ---")
        await tick(pc_id, state, t)
        state.time += 1
        manager.save_state(state)


def run_game(character_id: str | None = None, max_turns: int = 50, scenario: str | None = None) -> None:
    asyncio.run(_run_game(scenario, character_id, max_turns))

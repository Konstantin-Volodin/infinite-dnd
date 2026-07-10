import asyncio

from src.agents.character.tools import Action, Attack, Speak, Travel, Wait
from src.engine.runtime.loop import (
    _STALL_QUIET_TICKS,
    _advance_grounded_objective,
    _campaign_outcome,
    _is_stalled,
    _minimum_action_minutes,
    _record_intervention,
    _record_resolution_if_needed,
    _run_game,
)
from src.engine.state.models import Character, HistoryEvent, Location, Quest, WorldState
from src.engine.state.operations import WorldOperations


def _state() -> WorldState:
    return WorldState(
        locations={"tavern": Location(id="tavern")},
        characters={"hero": Character(id="hero", role="warrior", location="tavern")},
        quests={"q1": Quest(id="q1", title="Clear the Cave", description="", owner="hero", plan=["scout", "clear"])},
    )


def _event(text: str) -> HistoryEvent:
    return HistoryEvent(text=text, location="tavern", characters=["hero"])


# ============ STALL DETECTION ============

def test_fresh_state_not_stalled():
    assert not _is_stalled(_state())


def test_quiet_ticks_trigger_stall():
    state = _state()
    state.time = _STALL_QUIET_TICKS
    assert _is_stalled(state)


def test_quest_advancement_resets_quiet_clock():
    state = _state()
    state.time = _STALL_QUIET_TICKS
    WorldOperations(state).advance_quest("q1", advance=True)
    assert state.last_quest_advance_time == state.time
    assert not _is_stalled(state)


def test_idle_chatter_triggers_stall():
    state = _state()
    for text in ('hero says: "hm"', "hero waits.", 'hero says to bob: "well?"', "hero waits.", 'hero says: "so..."'):
        state.history.append(_event(text))
    assert _is_stalled(state)


def test_mixed_recent_events_not_stalled():
    state = _state()
    for text in ('hero says: "hm"', "hero waits.", "hero picks up 'sword'.", "hero waits.", 'hero says: "so..."'):
        state.history.append(_event(text))
    assert not _is_stalled(state)


def test_fewer_than_window_idle_events_not_stalled():
    state = _state()
    for text in ("hero waits.", "hero waits."):
        state.history.append(_event(text))
    assert not _is_stalled(state)


def test_director_reset_suppresses_consecutive_fire():
    state = _state()
    state.time = _STALL_QUIET_TICKS
    assert _is_stalled(state)
    # what tick() does after a director beat: reset the clock; the beat lands a non-idle event
    state.last_quest_advance_time = state.time
    state.history.append(_event("A stranger bursts in demanding payment."))
    assert not _is_stalled(state)


# ============ TURN FEEDBACK ============

def test_resolution_without_state_event_is_recorded_for_player_feedback():
    state = _state()

    events = _record_resolution_if_needed(state, "hero", 0, "  Nothing useful is hidden here.  ")

    assert [event.text for event in events] == ["Nothing useful is hidden here."]
    assert events[0].location == "tavern"
    assert events[0].characters == ["hero"]


def test_existing_resolution_events_are_not_duplicated():
    state = _state()
    state.history.append(_event("hero finds a brass key."))

    events = _record_resolution_if_needed(state, "hero", 0, "found a brass key")

    assert [event.text for event in events] == ["hero finds a brass key."]


def test_direct_actions_have_deterministic_time_floors():
    assert _minimum_action_minutes(Travel(actor="hero", destination="road")) == 10
    assert _minimum_action_minutes(Wait(actor="hero")) == 5
    assert _minimum_action_minutes(Speak(actor="hero", message="hello")) == 1
    assert _minimum_action_minutes(Attack(actor="hero", target="bandit")) == 1
    assert _minimum_action_minutes(Action(actor="hero", description="search the archive")) == 5
    assert _minimum_action_minutes(Action(actor="hero", description="open the door")) == 1


def test_grounded_discovery_advances_search_objective_when_dm_does_not():
    state = _state()
    state.quests["q1"].plan = ["search tavern for clues", "clear the cave"]
    event = _event("hero learns: the bandits use the north tunnel.")
    state.history.append(event)

    results = _advance_grounded_objective(
        state,
        "hero",
        Action(actor="hero", description="search the bar for signs"),
        [event],
        {"q1": 0},
    )

    assert state.quests["q1"].current_step == 1
    assert state.characters["hero"].stats.xp == 10
    assert "Quest 'q1' updated" in results[0]


def test_grounded_objective_fallback_requires_new_evidence_and_matching_location():
    state = _state()
    state.quests["q1"].plan = ["search forest for clues"]

    assert _advance_grounded_objective(
        state,
        "hero",
        Action(actor="hero", description="search the tavern"),
        [_event("hero learns: the cellar is damp.")],
        {"q1": 0},
    ) == []
    state.quests["q1"].plan = ["search tavern for clues"]
    assert _advance_grounded_objective(
        state,
        "hero",
        Action(actor="hero", description="search the tavern"),
        [_event("hero searches but finds nothing useful.")],
        {"q1": 0},
    ) == []
    assert state.quests["q1"].current_step == 0


# ============ CAMPAIGN OUTCOME ============

def test_campaign_ends_in_victory_when_all_owned_quests_are_completed():
    state = _state()
    state.quests["q1"].status = "completed"
    state.quests["side"] = Quest(
        id="side",
        title="Return the Key",
        description="",
        owner="hero",
        status="Completed",
    )

    assert _campaign_outcome(state, "hero") == "completed"


def test_campaign_ends_in_defeat_when_resolved_owned_quest_failed():
    state = _state()
    state.quests["q1"].status = "failed"

    assert _campaign_outcome(state, "hero") == "failed"


def test_campaign_continues_with_active_owned_quest_or_no_owned_quests():
    state = _state()
    assert _campaign_outcome(state, "hero") is None

    state.quests["q1"].owner = "someone-else"
    assert _campaign_outcome(state, "hero") is None


def test_game_loop_stops_immediately_after_campaign_victory(monkeypatch):
    state = _state()
    ticks: list[int] = []
    logged_events: list[str] = []

    class Manager:
        run_id = "test-run"
        scenario = "demo"
        manifest = {"pc": "hero", "title": "Test Quest", "hook": "Finish it."}

        def __init__(self, **_kwargs): pass
        def init_state(self): return state
        def latest_snapshot_name(self): return None
        def save_state(self, _state): pass

    class Log:
        def __init__(self, **_kwargs): pass
        def log_event(self, event, **_kwargs): logged_events.append(event)
        def log_turn(self, _turn): pass
        def close(self): pass

    async def finish_quest(_pc_id, world, tick_index, _logger, _controller, _replay):
        ticks.append(tick_index)
        world.quests["q1"].status = "completed"

    async def skip_compaction(*_args): pass

    monkeypatch.setattr("src.engine.runtime.loop.StateManager", Manager)
    monkeypatch.setattr("src.engine.runtime.loop.Logger", Log)
    monkeypatch.setattr("src.engine.runtime.loop.tick", finish_quest)
    monkeypatch.setattr("src.engine.runtime.loop.compact_history", skip_compaction)

    asyncio.run(_run_game("demo", "hero", max_turns=5, new_character=None))

    assert ticks == [0]
    assert "campaign_completed" in logged_events


# ============ ESCALATION COUNTER ============

def test_record_intervention_targets_known_quest():
    state = _state()
    assert _record_intervention(state, "q1") == "q1"
    assert _record_intervention(state, "q1") == "q1"
    assert state.director_interventions == {"q1": 2}


def test_record_intervention_falls_back_to_world():
    state = _state()
    assert _record_intervention(state, None) == "world"
    assert _record_intervention(state, "no-such-quest") == "world"
    assert state.director_interventions == {"world": 2}

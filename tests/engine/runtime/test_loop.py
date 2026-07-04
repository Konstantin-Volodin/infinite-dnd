from src.engine.runtime.loop import _STALL_QUIET_TICKS, _is_stalled, _record_intervention
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

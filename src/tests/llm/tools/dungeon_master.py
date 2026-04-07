"""Live tests: dungeon master agent calls the right tools given scenarios."""

import logging
import sys

from src.engine.models import Quest
from src.llm.dungeon_master import DungeonMasterDeps, agent
from src.tests.utils import build_state, pick_character, run_scenario

PREFIX = "dungeon-master"


def test_narrate() -> bool:
    state = build_state()
    char = pick_character(state)
    history_count = len(state.history)
    narration = "The lantern light shivers across the wet stone."
    run_scenario(
        agent, PREFIX,
        prompt=(
            "You must call the `narrate` tool exactly once. "
            f'Set content exactly "{narration}" and prompts_character exactly "{char.id}". '
            "Do not use `create` or `modify`. "
            "When done, call `done`."
        ),
        deps=DungeonMasterDeps(
            state=state,
            last_action={
                "character_id": char.id,
                "tool": "action",
                "result": {"intent": f"{char.id} studies the room.", "status": "success"},
            },
            narrate_location=char.location,
        ),
        tool_name="narrate",
    )
    if len(state.history) != history_count + 1:
        raise AssertionError("expected narration to append exactly one history event")
    if state.history[-1].text != narration:
        raise AssertionError("narration was not written to history")
    logging.info(f"[PASS] narrate")
    return True


def test_create() -> bool:
    state = build_state()
    char = pick_character(state)
    history_count = len(state.history)
    location_id = "ancient-library"
    run_scenario(
        agent, PREFIX,
        prompt=(
            "You must call the `create` tool exactly once. "
            f'Create a location named "Ancient Library" with description "Dusty aisles of forgotten tomes." '
            f'Connect it to location "{char.location}". '
            "Do not use `narrate` or `modify`. "
            "When done, call `done`."
        ),
        deps=DungeonMasterDeps(state=state, narrate_location=char.location),
        tool_name="create",
    )
    new_location = state.locations.get(location_id)
    if not new_location:
        raise AssertionError(f"expected {location_id} to be created")
    if char.location not in new_location.connections:
        raise AssertionError("expected new location to connect back to the anchor location")
    if len(state.history) != history_count + 1:
        raise AssertionError("expected create to append exactly one history event")
    if state.history[-1].text != f"A new place becomes known: {location_id}.":
        raise AssertionError(f"unexpected create history event: {state.history[-1].text!r}")
    logging.info(f"[PASS] create")
    return True


def test_modify() -> bool:
    state = build_state()
    quest: Quest = next(iter(state.quests.values()))
    history_count = len(state.history)
    old_status = quest.status
    run_scenario(
        agent, PREFIX,
        prompt=(
            "You must call the `modify` tool exactly once. "
            f'Update quest "{quest.id}" to status "completed" because the main objective has been resolved. '
            "Do not use `narrate` or `create`. "
            "When done, call `done`."
        ),
        deps=DungeonMasterDeps(state=state),
        tool_name="modify",
    )
    if state.quests[quest.id].status != "completed":
        raise AssertionError("expected quest status to update")
    if len(state.history) != history_count + 1:
        raise AssertionError("expected modify to append exactly one history event")
    if state.history[-1].text != f"Quest '{quest.title}' changed from {old_status} to completed.":
        raise AssertionError(f"unexpected modify history event: {state.history[-1].text!r}")
    logging.info(f"[PASS] modify")
    return True


def run_suite() -> bool:
    scenarios = [test_narrate, test_create, test_modify]
    passed = sum(1 for fn in scenarios if fn())
    logging.info(f"Dungeon master agent: {passed}/{len(scenarios)} passed")
    return passed == len(scenarios)


if __name__ == "__main__":
    from src.tests.llm.server import live_server
    with live_server():
        sys.exit(0 if run_suite() else 1)

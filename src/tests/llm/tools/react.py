"""Live tests: action resolver agent resolves actions with the expected tools."""

import logging
import sys

from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from src.llm.action_resolver import ActionResolverDeps, agent, discover_exit as discover_exit_tool
from src.llm.server import create_model
from src.tests.utils import build_state, pick_character, run_scenario

PREFIX = "action_resolver"


def test_remember() -> bool:
    state = build_state()
    char = pick_character(state)
    history_count = len(state.history)
    knowledge = "The old fountain has a loose stone ring around its basin."
    output, _ = run_scenario(
        agent,
        PREFIX,
        prompt=(
            "You must call the `remember` tool exactly once. "
            f'Use knowledge exactly "{knowledge}". '
            "Do not call `add_detail`, `adjust_hp`, `update_quest`, `take`, or `drop`. "
            "Then call `done` with one short narration that mentions the fountain."
        ),
        deps=ActionResolverDeps(char=char, state=state, description="carefully inspects the old fountain"),
        tool_name="remember",
    )
    if knowledge not in char.knowledge:
        raise AssertionError(f"expected knowledge to be added, got {char.knowledge!r}")
    if len(state.history) != history_count + 1:
        raise AssertionError("expected remember to append exactly one history event")
    if state.history[-1].text != f"{char.id} learns: {knowledge}":
        raise AssertionError(f"unexpected knowledge history event: {state.history[-1].text!r}")
    if "fountain" not in output.lower():
        raise AssertionError(f"expected final narration to mention the fountain, got {output!r}")
    logging.info(f"[PASS] remember - {char.id}")
    return True


def test_discover_exit() -> bool:
    state = build_state()
    char = pick_character(state)
    history_count = len(state.history)
    location_name = "Hidden Cellar"
    description = "A narrow stone stair descends beneath the market fountain into a damp cellar."
    ctx = RunContext(
        deps=ActionResolverDeps(char=char, state=state, description="asks around about a hidden cellar"),
        model=create_model(),
        usage=RunUsage(),
        agent=agent,
    )
    output = discover_exit_tool(ctx, name=location_name, description=description)
    new_location = state.locations.get("hidden-cellar")
    if not new_location:
        raise AssertionError("expected hidden-cellar to be created")
    if char.location not in new_location.connections:
        raise AssertionError("expected discovered location to connect back to the acting character's location")
    if len(state.history) != history_count + 1:
        raise AssertionError("expected discover_exit to append exactly one history event")
    if state.history[-1].text != "A new place becomes known: hidden-cellar.":
        raise AssertionError(f"unexpected discover_exit history event: {state.history[-1].text!r}")
    if output != "Created location hidden-cellar.":
        raise AssertionError(f"unexpected discover_exit tool output: {output!r}")
    logging.info(f"[PASS] discover_exit - {char.id}")
    return True


def run_suite() -> bool:
    scenarios = [test_remember, test_discover_exit]
    passed = sum(1 for fn in scenarios if fn())
    logging.info(f"action_resolver agent: {passed}/{len(scenarios)} passed")
    return passed == len(scenarios)


if __name__ == "__main__":
    from src.tests.llm.server import live_server

    with live_server():
        sys.exit(0 if run_suite() else 1)
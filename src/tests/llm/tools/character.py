"""Live tests: character agent calls the right tools given scenarios."""

import logging
import sys

from src.llm.character import CharacterDeps, agent
from src.tests.utils import build_state, pick_character, pick_travel_target, run_scenario

PREFIX = "character"


def test_action() -> bool:
    state = build_state()
    char = pick_character(state)
    history_count = len(state.history)
    description = "carefully inspects the old fountain"
    run_scenario(
        agent, PREFIX,
        prompt=(
            "You must call the `action` tool exactly once. "
            "Do not use `speak` or `travel`. "
            f'Use description exactly "{description}". '
            "When done, call `done`."
        ),
        deps=CharacterDeps(char=char, state=state),
        tool_name="action",
    )
    if len(state.history) != history_count + 1:
        raise AssertionError("expected action to append exactly one history event")
    if not state.history[-1].text.startswith(f"{char.id} {description}"):
        raise AssertionError(f"unexpected action history event: {state.history[-1].text!r}")
    logging.info(f"[PASS] action - {char.id}")
    return True


def test_speak() -> bool:
    state = build_state()
    char = pick_character(state)
    history_count = len(state.history)
    message = "I have a feeling something important is happening nearby."
    run_scenario(
        agent, PREFIX,
        prompt=(
            "You must call the `speak` tool exactly once. "
            "Do not use `action` or `travel`. "
            f'Say exactly: "{message}". '
            "When done, call `done`."
        ),
        deps=CharacterDeps(char=char, state=state),
        tool_name="speak",
    )
    if len(state.history) != history_count + 1:
        raise AssertionError("expected speak to append exactly one history event")
    if state.history[-1].text != f'{char.id} says: "{message}"':
        raise AssertionError(f"unexpected speech history event: {state.history[-1].text!r}")
    logging.info(f"[PASS] speak - {char.id}")
    return True


def test_travel() -> bool:
    state = build_state()
    char = pick_character(state)
    origin = char.location
    target = pick_travel_target(state, char)
    history_count = len(state.history)
    run_scenario(
        agent, PREFIX,
        prompt=(
            "You must call the `travel` tool exactly once. "
            "Do not use `action` or `speak`. "
            f'Travel to "{target}". '
            "When done, call `done`."
        ),
        deps=CharacterDeps(char=char, state=state),
        tool_name="travel",
    )
    if char.location != target:
        raise AssertionError(f"expected location {target!r}, got {char.location!r}")
    if len(state.history) != history_count + 2:
        raise AssertionError("expected travel to append exactly two history events")
    if state.history[-2].text != f"{char.id} left from {origin}":
        raise AssertionError(f"unexpected travel departure: {state.history[-2].text!r}")
    if state.history[-1].text != f"{char.id} travelled to {target}":
        raise AssertionError(f"unexpected travel arrival: {state.history[-1].text!r}")
    logging.info(f"[PASS] travel - {char.id} -> {target}")
    return True


def run_suite() -> bool:
    scenarios = [test_action, test_speak, test_travel]
    passed = sum(1 for fn in scenarios if fn())
    logging.info(f"Character agent: {passed}/{len(scenarios)} passed")
    return passed == len(scenarios)


if __name__ == "__main__":
    from src.tests.llm.server import live_server
    with live_server():
        sys.exit(0 if run_suite() else 1)

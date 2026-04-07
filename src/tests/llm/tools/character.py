"""Live tests: character agent calls the right tools given scenarios."""

import asyncio
import logging
import sys

from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from src.llm.character import CharacterDeps, agent
from src.llm.server import create_model
from src.tests.utils import build_state, pick_character, pick_travel_target, run_scenario

PREFIX = "character"


async def _prepared_tool_schemas(deps: CharacterDeps) -> dict[str, dict]:
    ctx = RunContext(deps=deps, model=create_model(), usage=RunUsage(), agent=agent)
    result: dict[str, dict] = {}
    prepared_toolset = agent._output_toolset.prepared(agent._prepare_output_tools)
    for name, tool in (await prepared_toolset.get_tools(ctx)).items():
        result[name] = tool.tool_def.parameters_json_schema
    return result


def test_contextual_tool_options() -> bool:
    state = build_state()
    char = pick_character(state)
    other = next(candidate for candidate in state.characters.values() if candidate.id != char.id)
    other.location = char.location
    prepared = asyncio.run(_prepared_tool_schemas(CharacterDeps(char=char, state=state)))

    speak_target_schema = prepared["speak"]["properties"]["target"]
    expected_targets = [
        candidate.id
        for candidate in state.characters.values()
        if candidate.location == char.location and candidate.id != char.id
    ]
    string_branch = next(branch for branch in speak_target_schema.get("anyOf", []) if branch.get("type") == "string")
    if string_branch.get("enum") != expected_targets:
        raise AssertionError(f"expected speak target enum {expected_targets!r}, got {string_branch.get('enum')!r}")

    travel_location_schema = prepared["travel"]["properties"]["location"]
    expected_travel_options = [
        connection_id
        for connection_id in state.locations[char.location].connections
        if connection_id in state.locations
    ]
    if travel_location_schema.get("enum") != expected_travel_options:
        raise AssertionError(
            f"expected travel location enum {expected_travel_options!r}, got {travel_location_schema.get('enum')!r}"
        )
    logging.info(f"[PASS] contextual tool options - {char.id}")
    return True


def test_action() -> bool:
    state = build_state()
    char = pick_character(state)
    history_count = len(state.history)
    description = "carefully inspects the old fountain"
    run_scenario(
        agent, PREFIX,
        prompt=(
            "You must call the `action` tool exactly once. "
            "Do not use `speak`, `travel`, or `wait`. "
            f'Use description exactly "{description}". '
            "That one tool call ends the run."
        ),
        deps=CharacterDeps(char=char, state=state),
        tool_name="action",
        expect_done=False,
    )
    if len(state.history) <= history_count:
        raise AssertionError("expected action resolution to append at least one history event")
    if not state.history[-1].text.strip():
        raise AssertionError("expected action resolution to leave a non-empty narration in history")
    if state.history[-1].text == f"{char.id} {description}":
        raise AssertionError("expected action to resolve consequences, not only echo the raw intent")
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
            "Do not use `action`, `travel`, or `wait`. "
            f'Say exactly: "{message}". '
            "That one tool call ends the run."
        ),
        deps=CharacterDeps(char=char, state=state),
        tool_name="speak",
        expect_done=False,
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
            "Do not use `action`, `speak`, or `wait`. "
            f'Travel to "{target}". '
            "That one tool call ends the run."
        ),
        deps=CharacterDeps(char=char, state=state),
        tool_name="travel",
        expect_done=False,
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
    scenarios = [test_contextual_tool_options, test_action, test_speak, test_travel]
    passed = sum(1 for fn in scenarios if fn())
    logging.info(f"Character agent: {passed}/{len(scenarios)} passed")
    return passed == len(scenarios)


if __name__ == "__main__":
    from src.tests.llm.server import live_server
    with live_server():
        sys.exit(0 if run_suite() else 1)

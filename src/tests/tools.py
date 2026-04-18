"""Live tests — verify proposer agents emit correct intents and Resolver mutates state."""

import asyncio
import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any

from pydantic_ai import Agent, RunContext, capture_run_messages
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RunUsage, UsageLimits

from src.engine.state import Character, StateManager, WorldState
from src.agents.utils import create_model
from src.agents.character.agent import CharacterDeps, agent as character_agent
from src.agents.action_resolver.agent import (
    ActionResolverDeps,
    agent as resolver_agent,
    discover_exit as discover_exit_tool,
    resolve,
)
from src.agents.intents import ActionIntent, SpeakIntent, TravelIntent
from src.tests import LOG_DIR, stamp


# ── helpers ──────────────────────────────────────────────────────────────

_MODEL_SETTINGS: ModelSettings = {
    "temperature": 0.0,
    "max_tokens": 512,
    "parallel_tool_calls": False,
    "thinking": False,
}
_USAGE_LIMITS = UsageLimits(request_limit=4, output_tokens_limit=256)
_state_manager = StateManager()


def _build() -> WorldState:
    return _state_manager.init_state()


def _pick_char(state: WorldState) -> Character:
    return next(iter(state.characters.values()))


def _pick_travel_target(state: WorldState, char: Character) -> str:
    loc = state.locations.get(char.location)
    if not loc or not loc.connections:
        raise RuntimeError(f"No travel target for {char.location!r}")
    return loc.connections[0]


def _assert_tool(messages: list[Any], name: str) -> None:
    calls = [
        getattr(p, "tool_name", None)
        for m in messages for p in getattr(m, "parts", [])
        if getattr(p, "part_kind", None) == "tool-call"
    ]
    if name not in calls:
        raise AssertionError(f"expected {name!r}, saw {calls!r}")


def _run(
    agent: Any, prefix: str, prompt: str, deps: Any, tool: str, *, expect_done: bool = False,
) -> tuple[Any, list[Any]]:
    logging.info(f"  [{prefix}:{tool}] sending prompt ({len(prompt)} chars)...")
    with capture_run_messages() as msgs:
        result = agent.run_sync(prompt, deps=deps, model_settings=_MODEL_SETTINGS, usage_limits=_USAGE_LIMITS)
    calls = [
        getattr(p, "tool_name", None)
        for m in msgs for p in getattr(m, "parts", [])
        if getattr(p, "part_kind", None) == "tool-call"
    ]
    logging.info(f"  [{prefix}:{tool}] done — {len(msgs)} messages, tools called: {calls}")

    _assert_tool(msgs, tool)
    if expect_done:
        _assert_tool(msgs, "done")

    trace = [
        {"kind": type(m).__name__, "parts": [
            {"kind": getattr(p, "part_kind", type(p).__name__), "tool": getattr(p, "tool_name", None),
             "content": getattr(p, "content", None), "args": getattr(p, "args", None)}
            for p in getattr(m, "parts", [])
        ]}
        for m in msgs
    ]
    path = LOG_DIR / f"{stamp}-{prefix}-{tool}.md"
    path.write_text(
        f"# {prefix}: {tool}\n\n## Prompt\n{prompt}\n\n## Output\n{result.output!r}\n\n"
        f"## Trace\n```json\n{json.dumps(trace, indent=2, default=str)}\n```",
        encoding="utf-8",
    )
    return result.output, list(msgs)


# ── server ───────────────────────────────────────────────────────────────

def test_server_health() -> bool:
    url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1").removesuffix("/v1") + "/health"
    try:
        r = urllib.request.urlopen(url, timeout=5)
        ok = r.status == 200
        r.close()
    except (urllib.error.URLError, urllib.error.HTTPError):
        ok = False
    logging.info(f"[{'PASS' if ok else 'FAIL'}] server health")
    return ok


def test_basic_completion() -> bool:
    a = Agent(create_model(), system_prompt="reply with one word only.", output_type=str)
    resp = a.run_sync("Say 'hello'.", model_settings={"temperature": 0.0, "thinking": False}).output
    ok = isinstance(resp, str) and len(resp.strip()) > 0
    logging.info(f"[{'PASS' if ok else 'FAIL'}] basic completion — {resp!r}")
    return ok


# ── character (intent generator) ─────────────────────────────────────────

def test_character_contextual_tools() -> bool:
    state = _build()
    char = _pick_char(state)
    other = next(c for c in state.characters.values() if c.id != char.id)
    other.location = char.location

    deps = CharacterDeps(char=char, state=state)
    ctx = RunContext(deps=deps, model=create_model(), usage=RunUsage(), agent=character_agent)
    prepared = character_agent._output_toolset.prepared(character_agent._prepare_output_tools)
    tools = {n: t.tool_def for n, t in asyncio.run(prepared.get_tools(ctx)).items()}

    expected_targets = [c.id for c in state.characters.values() if c.location == char.location and c.id != char.id]
    for t in expected_targets:
        assert t in tools["speak"].description, f"speak description missing target {t!r}"

    assert "travel" in tools, "travel tool should exist when connections are available"
    expected_travel = [cid for cid in state.locations[char.location].connections if cid in state.locations]
    for loc in expected_travel:
        assert loc in tools["travel"].description, f"travel description missing option {loc!r}"

    logging.info(f"[PASS] character contextual tools — {char.id}")
    return True


def test_character_action_intent() -> bool:
    state = _build()
    char = _pick_char(state)
    before = len(state.history)
    intent, _ = _run(
        character_agent, "character",
        f'Call `action` once with description "carefully inspects the old fountain". No other tools.',
        CharacterDeps(char=char, state=state), "action",
    )
    assert isinstance(intent, ActionIntent), f"expected ActionIntent, got {type(intent).__name__}"
    assert intent.actor == char.id
    assert len(state.history) == before, "character agent must not mutate state"

    # Resolver executes it
    asyncio.run(resolve(intent, state))
    assert len(state.history) > before, "resolve(action) should append history"
    logging.info(f"[PASS] character action intent — {char.id}")
    return True


def test_character_speak_intent() -> bool:
    state = _build()
    char = _pick_char(state)
    before = len(state.history)
    msg = "I have a feeling something important is happening nearby."
    intent, _ = _run(
        character_agent, "character",
        f'Call `speak` once with message exactly "{msg}". No other tools.',
        CharacterDeps(char=char, state=state), "speak",
    )
    assert isinstance(intent, SpeakIntent)
    assert intent.actor == char.id and intent.message == msg
    assert len(state.history) == before, "character agent must not mutate state"

    asyncio.run(resolve(intent, state))
    assert state.history[-1].text == f'{char.id} says: "{msg}"'
    logging.info(f"[PASS] character speak intent — {char.id}")
    return True


def test_character_travel_intent() -> bool:
    state = _build()
    char = _pick_char(state)
    target = _pick_travel_target(state, char)
    before = len(state.history)
    intent, _ = _run(
        character_agent, "character",
        f'Call `travel` once to "{target}". No other tools.',
        CharacterDeps(char=char, state=state), "travel",
    )
    assert isinstance(intent, TravelIntent)
    assert intent.actor == char.id and intent.destination == target
    assert len(state.history) == before, "character agent must not mutate state"
    assert char.location != target, "character agent must not move the character"

    asyncio.run(resolve(intent, state))
    assert char.location == target
    assert state.history[-1].text == f"{char.id} moved to '{target}'."
    logging.info(f"[PASS] character travel intent — {char.id} -> {target}")
    return True


# ── resolver sub-agent (free-form ActionIntent path) ────────────────────

def test_resolver_remember() -> bool:
    state = _build()
    char = _pick_char(state)
    before = len(state.history)
    knowledge = "The old fountain has a loose stone ring around its basin."
    output, _ = _run(
        resolver_agent, "resolver",
        f'Call `remember` once with knowledge exactly "{knowledge}". Then call `done` mentioning the fountain.',
        ActionResolverDeps(char=char, state=state, description="carefully inspects the old fountain"),
        "remember", expect_done=True,
    )
    assert knowledge in char.knowledge
    assert len(state.history) == before + 1
    assert state.history[-1].text == f"{char.id} learns: {knowledge}"
    assert "fountain" in output.lower(), f"done output should mention fountain: {output!r}"
    logging.info(f"[PASS] resolver remember — {char.id}")
    return True


def test_resolver_discover_exit() -> bool:
    state = _build()
    char = _pick_char(state)
    ctx = RunContext(
        deps=ActionResolverDeps(char=char, state=state, description="asks about a hidden cellar"),
        model=create_model(), usage=RunUsage(), agent=resolver_agent,
    )
    output = discover_exit_tool(ctx, name="Hidden Cellar", description="A narrow stone stair descends into a damp cellar.")
    loc = state.locations.get("hidden-cellar")
    assert loc, "hidden-cellar should be created"
    assert char.location in loc.connections
    assert output == "Location 'hidden-cellar' added."
    logging.info(f"[PASS] resolver discover_exit — {char.id}")
    return True


# ── runner ───────────────────────────────────────────────────────────────

def run_all() -> bool:
    if not test_server_health() or not test_basic_completion():
        return False

    tests = [
        test_character_contextual_tools,
        test_character_action_intent,
        test_character_speak_intent,
        test_character_travel_intent,
        test_resolver_remember,
        test_resolver_discover_exit,
    ]
    passed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            logging.error(f"[FAIL] {t.__name__}: {e}")
    logging.info(f"Total: {passed}/{len(tests)} passed")
    return passed == len(tests)

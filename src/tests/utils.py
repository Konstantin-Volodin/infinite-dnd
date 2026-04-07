"""Shared test utilities."""

import json
import logging
from datetime import datetime
from typing import Any

from pydantic_ai import capture_run_messages

from src.tests import LOG_DIR, stamp
from src.core.models import Character, WorldState
from src.core.state import StateManager


def build_state() -> WorldState:
    return StateManager().generate_initial_setup()


def pick_character(state: WorldState) -> Character:
    return next(iter(state.characters.values()))


def pick_travel_target(state: WorldState, char: Character) -> str:
    location = state.locations.get(char.location)
    if not location or not location.connections:
        raise RuntimeError(f"No connected travel target exists for {char.location!r}")
    return location.connections[0]


def assert_tool_call(messages: list[Any], tool_name: str) -> None:
    tool_calls = [
        getattr(part, "tool_name", None)
        for message in messages
        for part in getattr(message, "parts", [])
        if getattr(part, "part_kind", None) == "tool-call"
    ]
    if tool_name not in tool_calls:
        raise AssertionError(f"expected tool call {tool_name!r}, saw {tool_calls!r}")


def write_archive(prefix: str, name: str, prompt: str, output: str, messages: list[Any]) -> None:
    path = LOG_DIR / f"{stamp}-{prefix}-{name}.md"

    trace = []
    for message in messages:
        parts = []
        for part in getattr(message, "parts", []):
            parts.append({
                "kind": getattr(part, "part_kind", type(part).__name__),
                "tool": getattr(part, "tool_name", None),
                "content": getattr(part, "content", None),
                "args": getattr(part, "args", None),
            })
        trace.append({"kind": type(message).__name__, "parts": parts})

    content = [
        f"# {prefix.title()} Scenario: {name}",
        "",
        "## Prompt",
        prompt,
        "",
        "## Output",
        output,
        "",
        "## Message Trace",
        "```json",
        json.dumps(trace, indent=2, default=str),
        "```",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    logging.info(f"saved archive trace to {path}")


def run_scenario(
    agent: Any,
    prefix: str,
    prompt: str,
    deps: Any,
    tool_name: str,
    *,
    expect_done: bool = True,
) -> tuple[str, list[Any]]:
    with capture_run_messages() as messages:
        result = agent.run_sync(prompt, deps=deps)
    assert isinstance(result.output, str)
    assert_tool_call(messages, tool_name)
    if expect_done:
        assert_tool_call(messages, "done")
    write_archive(prefix, tool_name, prompt, result.output, messages)
    return result.output, list(messages)

"""Live tests: character agent calls the right tools given scenarios."""
from __future__ import annotations

import logging
import sys
from datetime import datetime

from pydantic_ai.messages import ToolCallPart

from src.tests import ARCHIVE_DIR
from src.llm.character import agent, CharacterDeps
from src.core.models import WorldState
from src.core.state import StateManager


# --- helpers ---

def _tool_calls(result) -> list[str]:
    return [
        part.tool_name
        for msg in result.all_messages()
        for part in msg.parts
        if isinstance(part, ToolCallPart)
    ]


def _archive(tool: str, char_id: str, scenario: str, passed: bool, calls: list[str], output: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d")
    content  = f"##### Tool: {tool} | {char_id} — {'PASS' if passed else 'FAIL'}\n\n"
    content += f"##### Scenario\n{scenario}\n\n"
    content += f"##### Tool Calls\n{calls}\n\n"
    content += f"##### Response\n{output}\n"
    path = ARCHIVE_DIR / f"{stamp}-{tool}-{char_id}.md"
    path.write_text(content, encoding="utf-8")
    logging.info(f"[{'PASS' if passed else 'FAIL'}] {tool}:{char_id} → {path}")


def _run(char_id: str, state: WorldState, scenario: str) -> tuple[list[str], str]:
    char = state.characters[char_id]
    result = agent.run_sync(scenario, deps=CharacterDeps(char=char, state=state))
    return _tool_calls(result), result.output


# --- tests ---

def test_perform_action(state: WorldState) -> dict[str, bool]:
    scenario = "A locked iron chest sits in the corner of the room. You want to force it open."
    results = {}
    for char_id in state.characters:
        calls, output = _run(char_id, state, scenario)
        passed = "perform_action" in calls
        _archive("perform_action", char_id, scenario, passed, calls, output)
        results[char_id] = passed
    return results


def test_speak(state: WorldState) -> dict[str, bool]:
    scenario = "The merchant is eyeing you suspiciously. You want to calm them down and explain yourself."
    results = {}
    for char_id in state.characters:
        calls, output = _run(char_id, state, scenario)
        passed = "speak" in calls
        _archive("speak", char_id, scenario, passed, calls, output)
        results[char_id] = passed
    return results


def test_travel(state: WorldState) -> dict[str, bool]:
    results = {}
    for char_id, char in state.characters.items():
        loc = state.locations.get(char.location)
        if not loc or not loc.connections:
            logging.warning(f"[SKIP] travel:{char_id} — no connections from {char.location!r}")
            continue
        dest = loc.connections[0]
        scenario = f"You've finished what you needed here. Time to move on — head to {dest}."
        calls, output = _run(char_id, state, scenario)
        passed = "travel" in calls
        _archive("travel", char_id, scenario, passed, calls, output)
        results[char_id] = passed
    return results


# --- runner ---

def main():
    state = StateManager().generate_state()
    all_results: dict[str, dict[str, bool]] = {
        "perform_action": test_perform_action(state),
        "speak":          test_speak(state),
        "travel":         test_travel(state),
    }

    total = passed = 0
    for tool, results in all_results.items():
        for char_id, ok in results.items():
            total += 1
            passed += ok
    logging.info(f"Character agent: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

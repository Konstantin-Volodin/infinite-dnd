"""Live tests: character agent calls the right tools given scenarios."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any

from pydantic_ai import ModelMessage, ModelResponse, ToolCallPart, capture_run_messages, models
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.tests import ARCHIVE_DIR
from src.core.models import Character, WorldState
from src.core.state import StateManager
from src.llm.character import CharacterDeps, agent

models.ALLOW_MODEL_REQUESTS = False


def build_state() -> WorldState:
    return StateManager().generate_initial_setup()


def pick_character(state: WorldState) -> Character:
    return next(iter(state.characters.values()))


def pick_travel_target(state: WorldState, char: Character) -> str:
    location = state.locations.get(char.location)
    if not location or not location.connections:
        raise RuntimeError(f"No connected travel target exists for {char.location!r}")
    return location.connections[0]


def output_arguments(tool_definition: Any) -> dict[str, Any]:
    schema = tool_definition.parameters_json_schema or {}
    properties = schema.get("properties", {})
    required = schema.get("required") or list(properties.keys())

    def example_value(field_schema: dict[str, Any]) -> Any:
        field_type = field_schema.get("type")
        if field_type == "integer":
            return 1
        if field_type == "number":
            return 1.0
        if field_type == "boolean":
            return True
        if field_type == "array":
            return []
        if field_type == "object":
            return {}
        return "final output"

    return {
        field_name: example_value(properties.get(field_name, {}))
        for field_name in required
    }


def make_forced_model(tool_name: str, tool_args: dict[str, Any]) -> FunctionModel:
    def model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            return ModelResponse(parts=[ToolCallPart(tool_name, tool_args)])

        output_tool = info.output_tools[0]
        return ModelResponse(parts=[ToolCallPart(output_tool.name, output_arguments(output_tool))])

    return FunctionModel(model_function)


def assert_tool_call(messages: list[Any], tool_name: str) -> None:
    tool_calls = [
        getattr(part, "tool_name", None)
        for message in messages
        for part in getattr(message, "parts", [])
        if getattr(part, "part_kind", None) == "tool-call"
    ]
    if tool_name not in tool_calls:
        raise AssertionError(f"expected tool call {tool_name!r}, saw {tool_calls!r}")


def write_archive(name: str, prompt: str, output: str, messages: list[Any]) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = ARCHIVE_DIR / f"{stamp}-character-{name}.md"

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
        f"# Character Scenario: {name}",
        "",
        f"## Prompt",
        prompt,
        "",
        f"## Output",
        output,
        "",
        "## Message Trace",
        "```json",
        json.dumps(trace, indent=2, default=str),
        "```",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    logging.info(f"saved archive trace to {path}")


def run_scenario(prompt: str, deps: CharacterDeps, tool_name: str, tool_args: dict[str, Any]) -> str:
    model = make_forced_model(tool_name, tool_args)
    with capture_run_messages() as messages:
        with agent.override(model=model):
            result = agent.run_sync(prompt, deps=deps)

    assert isinstance(result.output, str)
    assert result.output.strip()
    assert_tool_call(messages, tool_name)
    assert_tool_call(messages, "return_message")
    write_archive(tool_name, prompt, result.output, messages)
    return result.output


def test_action() -> bool:
    state = build_state()
    char = pick_character(state)
    output = run_scenario(
        prompt=f"{char.id}, carefully inspect your surroundings and act on the most important clue.",
        deps=CharacterDeps(char=char, state=state),
        tool_name="action",
        tool_args={"description": "carefully inspect your surroundings and act on the most important clue"},
    )
    logging.info(f"[PASS] action - {char.id}: {output!r}")
    return True


def test_speak() -> bool:
    state = build_state()
    char = pick_character(state)
    output = run_scenario(
        prompt=f"{char.id}, say something useful to the people nearby.",
        deps=CharacterDeps(char=char, state=state),
        tool_name="speak",
        tool_args={"message": "I have a feeling something important is happening nearby."},
    )
    logging.info(f"[PASS] speak - {char.id}: {output!r}")
    return True


def test_travel() -> bool:
    state = build_state()
    char = pick_character(state)
    target_location = pick_travel_target(state, char)
    output = run_scenario(
        prompt=f"{char.id}, travel to {target_location}.",
        deps=CharacterDeps(char=char, state=state),
        tool_name="travel",
        tool_args={"location": target_location},
    )
    logging.info(f"[PASS] travel - {char.id} -> {target_location}: {output!r}")
    return True


def main() -> bool:
    scenarios = [
        ("action", test_action),
        ("speak", test_speak),
        ("travel", test_travel),
    ]

    total = len(scenarios)
    passed = sum(1 for _, scenario in scenarios if scenario())
    logging.info(f"Character agent: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

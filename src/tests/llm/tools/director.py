"""Live tests: director agent calls the right tools given scenarios."""

import json
import logging
import sys
from datetime import datetime
from typing import Any

from pydantic_ai import ModelMessage, ModelResponse, ToolCallPart, capture_run_messages, models
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.core.models import Character, WorldState
from src.core.state import StateManager
from src.llm.director import DirectorDeps, agent
from src.tests import ARCHIVE_DIR

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


def get_tool_call_args(messages: list[Any], tool_name: str) -> dict[str, Any]:
    for message in messages:
        for part in getattr(message, "parts", []):
            if getattr(part, "part_kind", None) != "tool-call":
                continue
            if getattr(part, "tool_name", None) == tool_name:
                args = getattr(part, "args", None)
                if isinstance(args, dict):
                    return args
                raise AssertionError(f"expected dict args for {tool_name!r}, got {args!r}")
    raise AssertionError(f"expected tool call args for {tool_name!r}")


def write_archive(name: str, prompt: str, output: str, messages: list[Any]) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = ARCHIVE_DIR / f"{stamp}-director-{name}.md"

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
        f"# Director Scenario: {name}",
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
    prompt: str,
    deps: DirectorDeps,
    tool_name: str,
    tool_args: dict[str, Any],
) -> tuple[str, list[Any]]:
    model = make_forced_model(tool_name, tool_args)
    with capture_run_messages() as messages:
        with agent.override(model=model):
            result = agent.run_sync(prompt, deps=deps)

    assert isinstance(result.output, str)
    assert result.output.strip()
    assert_tool_call(messages, tool_name)
    assert_tool_call(messages, "return_message")
    write_archive(tool_name, prompt, result.output, messages)
    return result.output, list(messages)


def test_action() -> bool:
    state = build_state()
    char = pick_character(state)
    deps = DirectorDeps(state=state)
    output, messages = run_scenario(
        prompt="Choose a character to investigate the most important clue.",
        deps=deps,
        tool_name="action",
        tool_args={"character_id": char.id, "description": "carefully inspects the old fountain"},
    )
    tool_args = get_tool_call_args(messages, "action")
    if tool_args.get("character_id") != char.id:
        raise AssertionError(f"expected acted character {char.id!r}, got {tool_args.get('character_id')!r}")
    if char.id not in state.history[-1].text:
        raise AssertionError("expected action to write a character history event")
    logging.info(f"[PASS] action: {output!r}")
    return True


def test_speak() -> bool:
    state = build_state()
    char = pick_character(state)
    deps = DirectorDeps(state=state)
    output, _ = run_scenario(
        prompt="Choose a character to speak to the group.",
        deps=deps,
        tool_name="speak",
        tool_args={
            "character_id": char.id,
            "message": "We need to keep moving before the trail goes cold.",
        },
    )
    if "We need to keep moving before the trail goes cold." not in state.history[-1].text:
        raise AssertionError("expected speech to write dialogue to history")
    logging.info(f"[PASS] speak: {output!r}")
    return True


def test_travel() -> bool:
    state = build_state()
    char = pick_character(state)
    target_location = pick_travel_target(state, char)
    deps = DirectorDeps(state=state)
    output, _ = run_scenario(
        prompt="Choose a character to move the scene forward by traveling.",
        deps=deps,
        tool_name="travel",
        tool_args={"character_id": char.id, "location": target_location},
    )
    if state.characters[char.id].location != target_location:
        raise AssertionError("expected travel to update the chosen character location")
    logging.info(f"[PASS] travel: {output!r}")
    return True


def main() -> bool:
    scenarios = [
        ("action", test_action),
        ("speak", test_speak),
        ("travel", test_travel),
    ]

    total = len(scenarios)
    passed = sum(1 for _, scenario in scenarios if scenario())
    logging.info(f"Director agent: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
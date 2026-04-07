"""Live tests: dungeon master agent calls the right tools given scenarios."""

import json
import logging
import sys
from datetime import datetime
from typing import Any

from pydantic_ai import ModelMessage, ModelResponse, ToolCallPart, capture_run_messages, models
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.core.models import Character, Quest, WorldState
from src.core.state import StateManager
from src.llm.dungeon_master import DungeonMasterDeps, agent
from src.tests import ARCHIVE_DIR

models.ALLOW_MODEL_REQUESTS = False


def build_state() -> WorldState:
    return StateManager().generate_initial_setup()


def pick_character(state: WorldState) -> Character:
    return next(iter(state.characters.values()))


def pick_quest(state: WorldState) -> Quest:
    return next(iter(state.quests.values()))


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
    path = ARCHIVE_DIR / f"{stamp}-dungeon-master-{name}.md"

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
        f"# Dungeon Master Scenario: {name}",
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
    deps: DungeonMasterDeps,
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


def test_narrate() -> bool:
    state = build_state()
    char = pick_character(state)
    deps = DungeonMasterDeps(
        state=state,
        last_action={
            "character_id": char.id,
            "tool": "action",
            "result": {"intent": f"{char.id} studies the room.", "status": "success"},
        },
        narrate_location=char.location,
    )
    output, messages = run_scenario(
        prompt="React to the latest character action.",
        deps=deps,
        tool_name="narrate",
        tool_args={
            "content": "The lantern light shivers across the wet stone.",
            "prompts_character": char.id,
        },
    )
    tool_args = get_tool_call_args(messages, "narrate")
    if tool_args.get("prompts_character") != char.id:
        raise AssertionError(f"expected prompted_character {char.id!r}, got {tool_args.get('prompts_character')!r}")
    if state.history[-1].text != "The lantern light shivers across the wet stone.":
        raise AssertionError("narration was not written to history")
    logging.info(f"[PASS] narrate: {output!r}")
    return True


def test_create() -> bool:
    state = build_state()
    char = pick_character(state)
    deps = DungeonMasterDeps(state=state, narrate_location=char.location)
    output, _ = run_scenario(
        prompt="Create a new explorable location.",
        deps=deps,
        tool_name="create",
        tool_args={
            "type": "location",
            "name": "Ancient Library",
            "description": "Dusty aisles of forgotten tomes.",
            "location": char.location,
        },
    )
    new_location = state.locations.get("ancient-library")
    if not new_location:
        raise AssertionError("expected ancient-library to be created")
    if char.location not in new_location.connections:
        raise AssertionError("expected new location to connect back to the anchor location")
    logging.info(f"[PASS] create: {output!r}")
    return True


def test_modify() -> bool:
    state = build_state()
    quest = pick_quest(state)
    deps = DungeonMasterDeps(state=state)
    output, _ = run_scenario(
        prompt="Advance a quest after the latest development.",
        deps=deps,
        tool_name="modify",
        tool_args={
            "action": "update_quest",
            "target_id": quest.id,
            "status": "completed",
            "reason": "The main objective has been resolved.",
        },
    )
    if state.quests[quest.id].status != "completed":
        raise AssertionError("expected quest status to update")
    logging.info(f"[PASS] modify: {output!r}")
    return True


def main() -> bool:
    scenarios = [
        ("narrate", test_narrate),
        ("create", test_create),
        ("modify", test_modify),
    ]

    total = len(scenarios)
    passed = sum(1 for _, scenario in scenarios if scenario())
    logging.info(f"Dungeon master agent: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
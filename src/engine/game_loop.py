# src/engine/game_loop.py
"""Orchestrates the game loop: character acts, others react."""

import asyncio
import json
from typing import Any

from pydantic_ai import Agent
from pydantic_ai._agent_graph import CallToolsNode, ModelRequestNode
from pydantic_ai.usage import UsageLimits
from pydantic_graph import End

from src.core.models import WorldState
from src.core.state import StateManager
from src.llm.character import CharacterDeps, agent as character_agent
from src.llm.dungeon_master import DungeonMasterDeps, agent as dm_agent

_NO_LIMIT = UsageLimits(request_limit=None)


async def _run_logged(agent: Agent, prompt: str, **kwargs) -> Any:
    """Run an agent, printing each LLM request and tool call as it happens."""
    req_count = 0
    async with agent.iter(prompt, **kwargs) as agent_run:
        async for node in agent_run:
            if isinstance(node, ModelRequestNode):
                req_count += 1
                print(f"    [req #{req_count}]", flush=True)
            elif isinstance(node, CallToolsNode):
                for part in node.model_response.parts:
                    tool_name = getattr(part, "tool_name", None)
                    if tool_name:
                        print(f"    [tool: {tool_name}]", flush=True)
    return agent_run.result


def _run(agent: Agent, prompt: str, **kwargs) -> Any:
    return asyncio.get_event_loop().run_until_complete(_run_logged(agent, prompt, **kwargs))


def _args_dict(part: Any) -> dict:
    args = getattr(part, "args", {})
    if hasattr(args, "args_as_dict"):
        return args.args_as_dict()
    if isinstance(args, str):
        return json.loads(args) if args else {}
    if isinstance(args, dict):
        return args
    return {}


def _tool_calls(messages: list) -> list[tuple[str, dict]]:
    result = []
    for msg in messages:
        for part in getattr(msg, "parts", []):
            if getattr(part, "part_kind", None) == "tool-call":
                name = getattr(part, "tool_name", None)
                result.append((name, _args_dict(part)))
    return result


def _find_character(target: str, state: WorldState):
    if target in state.characters:
        return state.characters[target]
    target_lower = target.lower()
    for char in state.characters.values():
        if target_lower in char.id.lower():
            return char
    return None


def _print_history_since(state: WorldState, since: int) -> None:
    for event in state.history[since:]:
        print(f"  {event.text}")


def _dm_narrate(state: WorldState, location: str) -> None:
    last_event = state.history[-1] if state.history else None
    last_action = {"text": last_event.text} if last_event else None
    history_before = len(state.history)
    print("  [DM]", flush=True)
    _run(
        dm_agent,
        "Narrate the last action. Create or modify world elements if the scene calls for it.",
        deps=DungeonMasterDeps(state=state, last_action=last_action, narrate_location=location),
        usage_limits=_NO_LIMIT,
    )
    _print_history_since(state, history_before)


def run_turn(char_id: str, state: WorldState, message_history: list) -> list:
    """Run one character turn and react to each action. Returns updated message_history."""
    char = state.characters[char_id]

    print(f"  [{char.id}]", flush=True)
    history_before = len(state.history)

    result = _run(
        character_agent,
        "Play your turn. Act, speak, or travel as your character. Call done when you are finished.",
        deps=CharacterDeps(char=char, state=state),
        message_history=message_history or None,
        usage_limits=_NO_LIMIT,
    )
    message_history.extend(result.new_messages())

    for tool_name, args in _tool_calls(result.new_messages()):
        if tool_name == "done":
            break
        if tool_name == "travel":
            _print_history_since(state, history_before)
            history_before = len(state.history)
        elif tool_name == "speak" and args.get("target"):
            _print_history_since(state, history_before)
            history_before = len(state.history)
            target_char = _find_character(args["target"], state)
            if target_char and target_char.id != char.id:
                print(f"  [{target_char.id}]", flush=True)
                _run(
                    character_agent,
                    f'{char.id} just spoke to you: "{args.get("message", "")}". Respond in character.',
                    deps=CharacterDeps(char=target_char, state=state),
                    usage_limits=_NO_LIMIT,
                )
                _print_history_since(state, history_before)
                history_before = len(state.history)
        else:
            _print_history_since(state, history_before)
            history_before = len(state.history)
            _dm_narrate(state, char.location)
            history_before = len(state.history)

    return message_history


def run_game(character_id: str = "elara-swift", max_turns: int = 5) -> None:
    manager = StateManager()
    state = manager.generate_state()
    message_history: list = []

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")
        message_history = run_turn(character_id, state, message_history)
        state.time += 1
        manager.save_state(state)

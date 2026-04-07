# src/engine/game_loop.py
"""Orchestrates the game loop: character acts, others react."""

import asyncio
import json
import random
from contextlib import nullcontext
from typing import Any

from pydantic_ai import Agent
from pydantic_ai._agent_graph import ModelRequestNode
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits
from pydantic_graph import End

from src.engine.queries import resolve_character
from src.engine.models import WorldState
from src.engine.rules import get_skill_modifier
from src.engine.state import StateManager
from src.interface.logger import Logger
from src.llm.character.character import CHARACTER_RESPONSE_OUTPUTS, CharacterDeps, agent as character_agent
from src.llm.dungeon_master.dungeon_master import DungeonMasterDeps, agent as dm_agent

_PEEK = 60
_DISCOVERY_DC = 12
MAX_ACTIONS_PER_TURN = 5
_DM_REQUEST_LIMIT = UsageLimits(request_limit=20)   # safety net, not a behavioral constraint
_CHAR_ACTION_LIMIT = UsageLimits(request_limit=12)  # outer choice plus nested REACT resolution

_logger: Logger | None = None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _preview(text: str) -> str:
    text = text.replace("\n", " ").strip()
    return text[:_PEEK] + ("…" if len(text) > _PEEK else "")


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


def _print_history_since(state: WorldState, since: int) -> None:
    for event in state.history[since:]:
        print(f"  {event.text}")


def _roll(skill: str, char) -> tuple[int, int]:
    roll = random.randint(1, 20)
    mod = get_skill_modifier(char, skill)
    return roll + mod, roll


# ---------------------------------------------------------------------------
# Core run helper
# ---------------------------------------------------------------------------

async def _run_logged(agent: Agent, prompt: str, state: WorldState | None = None, label: str = "", **kwargs) -> Any:
    req_count = 0
    history_snapshot = len(state.history) if state else 0
    run_span = _logger.run(label) if _logger and label else nullcontext()

    with run_span:
        async with agent.iter(prompt, **kwargs) as agent_run:
            async for node in agent_run:
                if isinstance(node, ModelRequestNode):
                    req_count += 1
                    if state and req_count > 1:
                        _print_history_since(state, history_snapshot)
                        history_snapshot = len(state.history)
                elif isinstance(node, End) and state:
                    _print_history_since(state, history_snapshot)

            if _logger and label:
                _logger.log_messages(label, agent_run.result.all_messages())
        return agent_run.result


def _run(agent: Agent, prompt: str, state: WorldState | None = None, label: str = "", **kwargs) -> Any:
    return asyncio.get_event_loop().run_until_complete(
        _run_logged(agent, prompt, state=state, label=label, **kwargs)
    )


# ---------------------------------------------------------------------------
# DM actions
# ---------------------------------------------------------------------------

def _dm_narrate(state: WorldState, location: str) -> None:
    last_event = state.history[-1] if state.history else None
    last_action = {"text": last_event.text} if last_event else None
    print("  [DM]", flush=True)
    try:
        _run(
            dm_agent,
            (
                "React to the last action with one world narration. "
                "Do not write character dialogue. "
                "Use narrate at most once, then call done."
            ),
            state=state,
            label="dm:narrate",
            deps=DungeonMasterDeps(state=state, last_action=last_action, narrate_location=location),
            usage_limits=_DM_REQUEST_LIMIT,
        )
    except UsageLimitExceeded as exc:
        print(f"  [limit] DM narration ended early: {exc}", flush=True)


def _dm_introduce_location(name: str, state: WorldState, anchor: str) -> None:
    print(f"  [DM] introducing {name}…", flush=True)
    try:
        _run(
            dm_agent,
            (
                f'Create a new location called "{name}" and connect it to {anchor}. '
                "Use create at most once, narrate its discovery at most once, then call done. "
                "Do not write character dialogue."
            ),
            state=state,
            label=f"dm:create:{name}",
            deps=DungeonMasterDeps(state=state, narrate_location=anchor),
            usage_limits=_DM_REQUEST_LIMIT,
        )
    except UsageLimitExceeded as exc:
        print(f"  [limit] DM location introduction ended early: {exc}", flush=True)


# ---------------------------------------------------------------------------
# Turn runner
# ---------------------------------------------------------------------------

def run_turn(char_id: str, state: WorldState, session_history: list) -> list:
    char = state.characters[char_id]
    print(f"  [{char.id}]", flush=True)

    for i in range(MAX_ACTIONS_PER_TURN):
        deps = CharacterDeps(char=char, state=state)
        try:
            result = _run(
                character_agent,
                (
                    "Choose exactly ONE next step this run by calling action, speak, travel, or wait. "
                    "That one tool call ends this run. "
                    "The engine may call you again this turn with updated context, so focus only on the next immediate step. "
                    "The action tool resolves its own consequences."
                ),
                state=state,
                label=f"character:{char.id}:{i + 1}",
                deps=deps,
                message_history=session_history or None,
                usage_limits=_CHAR_ACTION_LIMIT,
            )
        except UsageLimitExceeded as exc:
            print(f"  [limit] {char.id}'s turn ended early: {exc}", flush=True)
            break
        session_history.extend(result.new_messages())

        tool_calls = _tool_calls(result.new_messages())
        action_call = tool_calls[-1] if tool_calls else None
        if not action_call:
            break

        tool_name, args = action_call
        if tool_name == "wait":
            break
        if tool_name == "travel":
            for dest in dict.fromkeys(deps.failed_travels):
                total, roll = _roll("investigation", char)
                if total >= _DISCOVERY_DC:
                    print(f"  [roll] investigation {roll}+mod={total} vs DC {_DISCOVERY_DC} → success", flush=True)
                    _dm_introduce_location(dest, state, char.location)
                else:
                    print(f"  [roll] investigation {roll}+mod={total} vs DC {_DISCOVERY_DC} → {dest} not found", flush=True)
        elif tool_name == "speak" and args.get("target"):
            target_char = resolve_character(state, args["target"])
            if target_char and target_char.id != char.id:
                print(f"  [{target_char.id}]", flush=True)
                _run(
                    character_agent,
                    (
                        f'{char.id} just spoke to you: "{args.get("message", "")}". '
                        "Respond in character with speak or wait. Choose exactly one tool call to end this run."
                    ),
                    state=state,
                    label=f"character:{target_char.id}:response",
                    deps=CharacterDeps(char=target_char, state=state),
                    output_type=CHARACTER_RESPONSE_OUTPUTS,
                )
        elif tool_name == "speak":
            _dm_narrate(state, char.location)
        elif tool_name == "action":
            continue
        else:
            _dm_narrate(state, char.location)

    return session_history


# ---------------------------------------------------------------------------
# Game entry point
# ---------------------------------------------------------------------------

def run_game(character_id: str = "elara-swift", max_turns: int = 5) -> None:
    global _logger
    _logger = Logger(character_id=character_id, max_turns=max_turns)

    try:
        manager = StateManager()
        state = manager.generate_initial_setup()
        session_history: list = []

        for turn in range(max_turns):
            print(f"\n--- Turn {turn + 1} ---")
            _logger.log_turn(turn + 1)
            session_history = run_turn(character_id, state, session_history)
            state.time += 1
            manager.save_state(state)
    finally:
        if _logger:
            _logger.close()
            _logger = None

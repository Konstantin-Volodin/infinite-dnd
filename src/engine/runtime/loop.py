"""Game loop: a character acts, the DM reacts."""

import random

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from src.engine.rules import get_skill_modifier
from src.engine.state import StateManager, WorldState, resolve_character
from src.engine.runtime.messages import extract_tool_calls
from src.agents.character.agent import CHARACTER_RESPONSE_OUTPUTS, CharacterDeps, agent as character_agent
from src.agents.dungeon_master.agent import DungeonMasterDeps, agent as dm_agent

_DISCOVERY_DC = 12
MAX_ACTIONS_PER_TURN = 5
_DM_REQUEST_LIMIT = UsageLimits(request_limit=20)
_CHAR_ACTION_LIMIT = UsageLimits(request_limit=12)


def _print_new(state: WorldState, since: int) -> None:
    for event in state.history[since:]:
        print(f"  {event.text}")


def _roll(skill: str, char) -> tuple[int, int]:
    roll = random.randint(1, 20)
    return roll + get_skill_modifier(char, skill), roll


def _dm_narrate(state: WorldState, location: str) -> None:
    last_event = state.history[-1] if state.history else None
    last_action = {"text": last_event.text} if last_event else None
    print("  [DM]", flush=True)
    before = len(state.history)
    try:
        dm_agent.run_sync(
            (
                "React to the last action with one world narration. "
                "Do not write character dialogue. "
                "Use narrate at most once, then call done."
            ),
            deps=DungeonMasterDeps(state=state, last_action=last_action, narrate_location=location),
            usage_limits=_DM_REQUEST_LIMIT,
        )
    except UsageLimitExceeded as exc:
        print(f"  [limit] DM narration ended early: {exc}", flush=True)
    _print_new(state, before)


def _dm_introduce_location(name: str, state: WorldState, anchor: str) -> None:
    print(f"  [DM] introducing {name}…", flush=True)
    before = len(state.history)
    try:
        dm_agent.run_sync(
            (
                f'Create a new location called "{name}" and connect it to {anchor}. '
                "Use create at most once, narrate its discovery at most once, then call done. "
                "Do not write character dialogue."
            ),
            deps=DungeonMasterDeps(state=state, narrate_location=anchor),
            usage_limits=_DM_REQUEST_LIMIT,
        )
    except UsageLimitExceeded as exc:
        print(f"  [limit] DM location introduction ended early: {exc}", flush=True)
    _print_new(state, before)


def run_turn(char_id: str, state: WorldState, session_history: list) -> list:
    char = state.characters[char_id]
    print(f"  [{char.id}]", flush=True)

    for _ in range(MAX_ACTIONS_PER_TURN):
        deps = CharacterDeps(char=char, state=state)
        before = len(state.history)
        try:
            result = character_agent.run_sync(
                (
                    "Choose exactly ONE next step this run by calling action, speak, travel, or wait. "
                    "That one tool call ends this run. "
                    "The engine may call you again this turn with updated context, so focus only on the next immediate step. "
                    "The action tool resolves its own consequences."
                ),
                deps=deps,
                message_history=session_history or None,
                usage_limits=_CHAR_ACTION_LIMIT,
            )
        except UsageLimitExceeded as exc:
            print(f"  [limit] {char.id}'s turn ended early: {exc}", flush=True)
            break

        session_history.extend(result.new_messages())
        _print_new(state, before)

        tool_calls = extract_tool_calls(result.new_messages())
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
                before_reply = len(state.history)
                character_agent.run_sync(
                    (
                        f'{char.id} just spoke to you: "{args.get("message", "")}". '
                        "Respond in character with speak or wait. Choose exactly one tool call to end this run."
                    ),
                    deps=CharacterDeps(char=target_char, state=state),
                    output_type=CHARACTER_RESPONSE_OUTPUTS,
                )
                _print_new(state, before_reply)
        elif tool_name == "speak":
            _dm_narrate(state, char.location)
        elif tool_name == "action":
            continue
        else:
            _dm_narrate(state, char.location)

    return session_history


def run_game(character_id: str = "elara-swift", max_turns: int = 5) -> None:
    manager = StateManager()
    state = manager.init_state()
    session_history: list = []

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")
        session_history = run_turn(character_id, state, session_history)
        state.time += 1
        manager.save_state(state)

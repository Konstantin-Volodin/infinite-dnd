"""Console PC controller — a human plays the acting character's turn from stdin.

Drop-in for `pc_controller` in `src.engine.runtime.loop`: same signature, same
`CharacterTool` output, so the rest of the engine (resolver, DM, replay
recording) doesn't need to know a human is behind the wheel.
"""

import asyncio

from src.agents.character.tools import Action, Attack, CharacterTool, Speak, Travel, Wait
from src.engine.rules import get_health_status
from src.engine.state import WorldState, characters_in_location, connected_location_ids, resolve_character, resolve_location_id

_HELP = "Type a plain sentence to act, or a command: /speak [target] <message> | /travel <place> | /attack <target> | /wait"


class _InputError(ValueError):
    """A malformed or unresolvable command — caller prints it and reprompts."""


def _describe_situation(actor_id: str, state: WorldState) -> str:
    char = state.characters[actor_id]
    loc = state.locations.get(char.location)
    lines = [f"\n=== Your turn: {actor_id} ==="]
    if loc:
        lines.append(f"Location: {loc.id} — {loc.description}" if loc.description else f"Location: {loc.id}")
        if loc.items:
            lines.append(f"Items here: {', '.join(loc.items)}")
    lines.append(
        f"HP: {char.stats.hp}/{char.stats.max_hp}  Gold: {char.stats.gold}  "
        f"Inventory: {', '.join(char.inventory) if char.inventory else 'none'}"
    )

    present = characters_in_location(state, char.location, exclude_character_id=actor_id)
    if present:
        lines.append("Present: " + ", ".join(f"{c.id} ({get_health_status(c)})" for c in present))

    connections = connected_location_ids(state, char.location)
    if connections:
        lines.append("Connections: " + ", ".join(connections))

    lines.append(f"\n{_HELP}")
    return "\n".join(lines)


def _split_speak_target(state: WorldState, rest: str) -> tuple[str | None, str]:
    """`/speak bob hello there` -> target 'bob', message 'hello there'; no match leaves it untargeted."""
    head, _, tail = rest.partition(" ")
    target = resolve_character(state, head)
    if target and tail:
        return target.id, tail
    return None, rest


def _parse_intent(actor_id: str, state: WorldState, line: str) -> CharacterTool:
    line = line.strip()
    if not line:
        raise _InputError(_HELP)
    if not line.startswith("/"):
        return Action(actor=actor_id, description=line)

    command, _, rest = line[1:].partition(" ")
    command, rest = command.lower(), rest.strip()

    if command == "wait":
        return Wait(actor=actor_id)
    if command == "travel":
        if not rest:
            raise _InputError("Usage: /travel <destination>")
        destination = resolve_location_id(state, rest)
        if destination is None:
            raise _InputError(f"Unknown destination '{rest}'.")
        return Travel(actor=actor_id, destination=destination)
    if command == "attack":
        if not rest:
            raise _InputError("Usage: /attack <target>")
        target = resolve_character(state, rest)
        if target is None:
            raise _InputError(f"Unknown target '{rest}'.")
        return Attack(actor=actor_id, target=target.id)
    if command == "speak":
        if not rest:
            raise _InputError("Usage: /speak [target] <message>")
        target_id, message = _split_speak_target(state, rest)
        return Speak(actor=actor_id, message=message, target=target_id)

    raise _InputError(f"Unknown command '/{command}'. {_HELP}")


async def console_pc_controller(actor_id: str, state: WorldState) -> CharacterTool:
    """Human-in-the-loop `pc_controller`: prints the situation, reprompts until input parses."""
    print(_describe_situation(actor_id, state), flush=True)
    while True:
        line = await asyncio.to_thread(input, "> ")
        try:
            return _parse_intent(actor_id, state, line)
        except _InputError as exc:
            print(f"  {exc}", flush=True)

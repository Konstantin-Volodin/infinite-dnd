"""Tool-call extraction from pydantic-ai message traces."""

import json
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class _ArgsAsDict(Protocol):
    def args_as_dict(self) -> dict[str, Any]: ...


def _args_dict(part: Any) -> dict[str, Any]:
    args = getattr(part, "args", {})
    if isinstance(args, _ArgsAsDict):
        return args.args_as_dict()
    if isinstance(args, str):
        return json.loads(args) if args else {}
    if isinstance(args, dict):
        return args
    return {}


def extract_tool_calls(messages: list[Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return (tool_name, args) pairs from a pydantic-ai message list, in order."""
    calls: list[tuple[str, dict[str, Any]]] = []
    for msg in messages:
        for part in getattr(msg, "parts", []):
            if getattr(part, "part_kind", None) == "tool-call":
                name = getattr(part, "tool_name", None)
                if name:
                    calls.append((name, _args_dict(part)))
    return calls

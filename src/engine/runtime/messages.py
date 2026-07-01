"""Tool-call extraction from pydantic-ai message traces."""

import json
from typing import Any


def _args_dict(part: Any) -> dict:
    args = getattr(part, "args", {})
    if hasattr(args, "args_as_dict"):
        return args.args_as_dict()
    if isinstance(args, str):
        return json.loads(args) if args else {}
    if isinstance(args, dict):
        return args
    return {}


def extract_tool_calls(messages: list) -> list[tuple[str, dict]]:
    """Return (tool_name, args) pairs from a pydantic-ai message list, in order."""
    calls: list[tuple[str, dict]] = []
    for msg in messages:
        for part in getattr(msg, "parts", []):
            if getattr(part, "part_kind", None) == "tool-call":
                name = getattr(part, "tool_name", None)
                if name:
                    calls.append((name, _args_dict(part)))
    return calls

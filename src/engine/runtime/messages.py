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


if __name__ == "__main__":
    import logging
    from types import SimpleNamespace

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    def part(kind: str, tool_name: str | None = None, args: Any = None):
        return SimpleNamespace(part_kind=kind, tool_name=tool_name, args=args)

    def msg(*parts):
        return SimpleNamespace(parts=list(parts))

    # empty
    assert extract_tool_calls([]) == []

    # mixed parts — only tool-call survives
    messages = [
        msg(part("text")),
        msg(
            part("tool-call", "speak", '{"message": "hi"}'),
            part("tool-call", "wait", {}),
        ),
        msg(part("tool-call", "travel", '')),  # empty string args → {}
        msg(part("tool-return", "speak", "ok")),  # not a tool-call → skipped
    ]
    result = extract_tool_calls(messages)
    assert result == [("speak", {"message": "hi"}), ("wait", {}), ("travel", {})], result

    # object with args_as_dict method
    class Args:
        def args_as_dict(self) -> dict:
            return {"x": 1}

    assert extract_tool_calls([msg(part("tool-call", "foo", Args()))]) == [("foo", {"x": 1})]

    logging.info(f"{__file__} tests completed successfully.")

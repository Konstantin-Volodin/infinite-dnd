from types import SimpleNamespace
from typing import Any

from src.engine.runtime.messages import extract_tool_calls


def _part(kind: str, tool_name: str | None = None, args: Any = None):
    return SimpleNamespace(part_kind=kind, tool_name=tool_name, args=args)


def _msg(*parts):
    return SimpleNamespace(parts=list(parts))


def test_empty():
    assert extract_tool_calls([]) == []


def test_mixed_parts_only_tool_call_survives():
    messages = [
        _msg(_part("text")),
        _msg(
            _part("tool-call", "speak", '{"message": "hi"}'),
            _part("tool-call", "wait", {}),
        ),
        _msg(_part("tool-call", "travel", '')),  # empty string args → {}
        _msg(_part("tool-return", "speak", "ok")),  # not a tool-call → skipped
    ]
    result = extract_tool_calls(messages)
    assert result == [("speak", {"message": "hi"}), ("wait", {}), ("travel", {})], result


def test_args_as_dict_method():
    class Args:
        def args_as_dict(self) -> dict:
            return {"x": 1}

    assert extract_tool_calls([_msg(_part("tool-call", "foo", Args()))]) == [("foo", {"x": 1})]

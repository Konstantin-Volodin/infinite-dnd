"""Helpers for loading and normalizing JSONL session logs."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

_TOOL_CALL_RE = re.compile(r"ToolCallPart\(tool_name='([^']+)'")
_TOOL_RETURN_RE = re.compile(r"ToolReturnPart\(tool_name='([^']+)'")
_WHITESPACE_RE = re.compile(r"\s+")
_MODEL_KIND_RE = re.compile(r"^(ModelRequest|ModelResponse)\(")
_MODEL_NAME_RE = re.compile(r"model_name='([^']+)'")
_PROVIDER_NAME_RE = re.compile(r"provider_name='([^']+)'")
_FINISH_REASON_RE = re.compile(r"finish_reason='([^']+)'")
_RUN_ID_RE = re.compile(r"run_id='([^']+)'")
_USAGE_RE = re.compile(
    r"usage=RequestUsage\(input_tokens=(?P<input_tokens>\d+)(?:, cache_read_tokens=(?P<cache_read_tokens>\d+))?(?:, output_tokens=(?P<output_tokens>\d+))?",
    re.S,
)
_SYSTEM_PROMPT_RE = re.compile(r"SystemPromptPart\(content=(?P<quote>['\"])(?P<content>.*?)(?P=quote), timestamp=", re.S)
_USER_PROMPT_RE = re.compile(r"UserPromptPart\(content=(?P<quote>['\"])(?P<content>.*?)(?P=quote), timestamp=", re.S)
_THINKING_RE = re.compile(r"ThinkingPart\(content=(?P<quote>['\"])(?P<content>.*?)(?P=quote), id=", re.S)
_INSTRUCTIONS_RE = re.compile(r"instructions=(?P<quote>['\"])(?P<content>.*?)(?P=quote)(?:, run_id=|\)$)", re.S)
_TOOL_CALL_DETAIL_RE = re.compile(
    r"ToolCallPart\(tool_name='(?P<tool>[^']+)', args='(?P<args>.*?)', tool_call_id='(?P<tool_call_id>[^']+)'",
    re.S,
)
_TOOL_RETURN_DETAIL_RE = re.compile(
    r"ToolReturnPart\(tool_name='(?P<tool>[^']+)', content='(?P<content>.*?)', tool_call_id='(?P<tool_call_id>[^']+)'",
    re.S,
)


def discover_log_files(path: Path) -> list[Path]:
    target = Path(path)
    if target.is_file():
        return [target]
    if not target.exists():
        return []
    return sorted(
        (candidate for candidate in target.glob("*.log") if candidate.is_file()),
        key=lambda candidate: candidate.name,
        reverse=True,
    )


def list_logs(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for candidate in discover_log_files(path):
        stat = candidate.stat()
        result.append(
            {
                "name": candidate.name,
                "path": str(candidate),
                "size_bytes": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
    return result


def load_session(path: Path) -> dict[str, Any]:
    log_path = Path(path)
    entries = _load_entries(log_path)
    runs = _build_runs(entries)
    turns = sorted({entry["turn"] for entry in entries if entry.get("turn") is not None})
    event_counts = Counter(entry["event"] for entry in entries)

    started = next((entry for entry in entries if entry["event"] == "game_session_started"), None)
    finished = next((entry for entry in reversed(entries) if entry["event"] == "game_session_finished"), None)
    first_time = _parse_time(entries[0].get("time")) if entries else None
    last_time = _parse_time(entries[-1].get("time")) if entries else None
    duration_s = round((last_time - first_time).total_seconds(), 3) if first_time and last_time else None

    return {
        "file": log_path.name,
        "path": str(log_path),
        "summary": {
            "character_id": started["raw"].get("character_id") if started else None,
            "max_turns": started["raw"].get("max_turns") if started else None,
            "turns_completed": finished["raw"].get("turns_completed") if finished else (max(turns) if turns else 0),
            "started_at": entries[0].get("time") if entries else None,
            "finished_at": entries[-1].get("time") if entries else None,
            "duration_s": duration_s,
        },
        "turns": turns,
        "event_types": sorted(event_counts.keys()),
        "event_counts": dict(event_counts),
        "stats": {
            "event_count": len(entries),
            "run_count": len(runs),
            "llm_message_count": event_counts.get("llm_message", 0),
            "error_count": event_counts.get("parse_error", 0),
        },
        "runs": runs,
        "entries": entries,
    }


def _load_entries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                entries.append(
                    {
                        "line": line_number,
                        "time": None,
                        "display_time": "unparsed",
                        "event": "parse_error",
                        "turn": None,
                        "label": None,
                        "summary": f"Could not parse log line {line_number}: {exc.msg}",
                        "excerpt": _compact(line, 280),
                        "message_kind": "parse_error",
                        "tool_calls": [],
                        "tool_returns": [],
                        "raw": {"line": line, "error": exc.msg},
                    }
                )
                continue
            entries.append(_normalize_entry(entry, line_number))
    return entries


def _normalize_entry(entry: dict[str, Any], line_number: int) -> dict[str, Any]:
    message = entry.get("message")
    message_text = _stringify(message)
    message_kind = _classify_message(message_text) if entry.get("event") == "llm_message" else None
    tool_calls = _unique(_TOOL_CALL_RE.findall(message_text)) if message_text else []
    tool_returns = _unique(_TOOL_RETURN_RE.findall(message_text)) if message_text else []
    return {
        "line": line_number,
        "time": entry.get("time"),
        "display_time": _display_time(entry.get("time")),
        "event": entry.get("event", "unknown"),
        "turn": entry.get("turn"),
        "label": entry.get("label"),
        "summary": _summarize_entry(entry, message_kind=message_kind, tool_calls=tool_calls, tool_returns=tool_returns),
        "excerpt": _compact(message_text, 320) if message_text else None,
        "message_kind": message_kind,
        "tool_calls": tool_calls,
        "tool_returns": tool_returns,
        "raw": entry,
        "raw_pretty": _format_raw_payload(entry),
    }


def _build_runs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    open_runs: dict[str, list[dict[str, Any]]] = {}

    for entry in entries:
        event = entry["event"]
        label = entry.get("label")
        if event == "agent_run_started" and label:
            run = {
                "id": f"run-{len(runs) + 1}",
                "label": label,
                "turn": entry.get("turn"),
                "started_at": entry.get("time"),
                "finished_at": None,
                "elapsed_s": None,
                "message_count": 0,
                "tool_calls": [],
                "message_kinds": [],
            }
            runs.append(run)
            open_runs.setdefault(label, []).append(run)
            continue

        if event == "llm_message" and label and label in open_runs and open_runs[label]:
            run = open_runs[label][-1]
            run["message_count"] += 1
            run["tool_calls"] = _unique([*run["tool_calls"], *entry.get("tool_calls", [])])
            message_kind = entry.get("message_kind")
            if message_kind:
                run["message_kinds"] = _unique([*run["message_kinds"], message_kind])
            continue

        if event == "agent_run_finished" and label and label in open_runs and open_runs[label]:
            run = open_runs[label].pop()
            run["finished_at"] = entry.get("time")
            run["elapsed_s"] = entry["raw"].get("elapsed_s")

    return runs


def _summarize_entry(entry: dict[str, Any], *, message_kind: str | None, tool_calls: list[str], tool_returns: list[str]) -> str:
    event = entry.get("event", "unknown")
    if event == "game_session_started":
        return f"Session started for {entry.get('character_id', 'unknown')} with max {entry.get('max_turns', '?')} turns."
    if event == "game_session_finished":
        return f"Session finished after {entry.get('turns_completed', 0)} turns."
    if event == "turn_started":
        return f"Turn {entry.get('turn')} started."
    if event == "agent_run_started":
        return f"{entry.get('label', 'agent')} started."
    if event == "agent_run_finished":
        elapsed = entry.get("elapsed_s")
        if elapsed is None:
            return f"{entry.get('label', 'agent')} finished."
        return f"{entry.get('label', 'agent')} finished in {elapsed}s."
    if event == "llm_message":
        prefix = (message_kind or "llm").replace("_", " ")
        message_text = _stringify(entry.get("message"))
        if tool_calls:
            return f"{prefix} issued tool call: {', '.join(tool_calls)}."
        if tool_returns:
            return f"{prefix} received tool return: {', '.join(tool_returns)}."
        if message_text:
            return f"{prefix}: {_compact(message_text, 160)}"
        return prefix
    return event.replace("_", " ")


def _classify_message(message_text: str) -> str:
    if message_text.startswith("ModelRequest("):
        return "model_request"
    if message_text.startswith("ModelResponse("):
        return "model_response"
    if "ToolReturnPart(" in message_text:
        return "tool_return"
    return "llm_message"


def _display_time(value: Any) -> str:
    timestamp = _parse_time(value)
    if not timestamp:
        return "unknown"
    return timestamp.strftime("%H:%M:%S")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def _compact(text: str, limit: int) -> str:
    compacted = _WHITESPACE_RE.sub(" ", text).strip()
    if len(compacted) <= limit:
        return compacted
    return compacted[: limit - 3].rstrip() + "..."


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _format_raw_payload(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in payload.items():
        if key == "message":
            lines.extend(_format_field(key, _format_message_payload(value), preformatted=True))
        else:
            lines.extend(_format_field(key, value))
    return "\n".join(lines)


def _format_field(name: str, value: Any, *, preformatted: bool = False) -> list[str]:
    if preformatted:
        text = str(value)
        return [f"{name}:", *_indent_lines(text.splitlines() or [""])]

    if value is None:
        return [f"{name}: null"]

    if isinstance(value, (bool, int, float)):
        return [f"{name}: {value}"]

    if isinstance(value, str):
        if "\n" in value:
            return [f"{name}:", *_indent_lines(value.splitlines())]
        return [f"{name}: {value}"]

    rendered = json.dumps(value, indent=2, ensure_ascii=False)
    return [f"{name}:", *_indent_lines(rendered.splitlines())]


def _format_message_payload(message: Any) -> str:
    if not isinstance(message, str):
        return json.dumps(message, indent=2, ensure_ascii=False)

    cleaned = _decode_log_text(message)
    kind_match = _MODEL_KIND_RE.match(message)
    if not kind_match:
        return cleaned

    lines = [kind_match.group(1)]
    metadata = _extract_message_metadata(message)
    if metadata:
        lines.append("metadata:")
        lines.extend(f"  {key}: {value}" for key, value in metadata)

    usage = _extract_message_usage(message)
    if usage:
        lines.append("usage:")
        lines.extend(f"  {key}: {value}" for key, value in usage)

    instructions = _extract_single_block(_INSTRUCTIONS_RE, message)
    if instructions:
        lines.append("instructions:")
        lines.extend(_indent_lines(instructions.splitlines() or [""]))

    part_lines = _extract_message_parts(message)
    if part_lines:
        lines.append("parts:")
        lines.extend(part_lines)

    if len(lines) == 1:
        return cleaned
    return "\n".join(lines)


def _extract_message_metadata(message: str) -> list[tuple[str, str]]:
    metadata: list[tuple[str, str]] = []
    for label, pattern in [
        ("model_name", _MODEL_NAME_RE),
        ("provider_name", _PROVIDER_NAME_RE),
        ("finish_reason", _FINISH_REASON_RE),
        ("run_id", _RUN_ID_RE),
    ]:
        match = pattern.search(message)
        if match:
            metadata.append((label, _decode_log_text(match.group(1))))
    return metadata


def _extract_message_usage(message: str) -> list[tuple[str, str]]:
    match = _USAGE_RE.search(message)
    if not match:
        return []

    fields = [
        ("input_tokens", match.group("input_tokens")),
        ("cache_read_tokens", match.group("cache_read_tokens")),
        ("output_tokens", match.group("output_tokens")),
    ]
    return [(key, value) for key, value in fields if value is not None]


def _extract_message_parts(message: str) -> list[str]:
    lines: list[str] = []

    for title, pattern in [
        ("SystemPromptPart", _SYSTEM_PROMPT_RE),
        ("UserPromptPart", _USER_PROMPT_RE),
        ("ThinkingPart", _THINKING_RE),
    ]:
        for match in pattern.finditer(message):
            lines.append(f"  - {title}")
            lines.append("    content:")
            lines.extend(_indent_lines((_decode_log_text(match.group("content")).splitlines() or [""]), prefix="      "))

    for match in _TOOL_CALL_DETAIL_RE.finditer(message):
        lines.append("  - ToolCallPart")
        lines.append(f"    tool_name: {match.group('tool')}")
        lines.append(f"    tool_call_id: {match.group('tool_call_id')}")
        lines.append("    args:")
        lines.extend(_indent_lines(_format_jsonish(_decode_log_text(match.group("args"))).splitlines() or [""], prefix="      "))

    for match in _TOOL_RETURN_DETAIL_RE.finditer(message):
        lines.append("  - ToolReturnPart")
        lines.append(f"    tool_name: {match.group('tool')}")
        lines.append(f"    tool_call_id: {match.group('tool_call_id')}")
        lines.append("    content:")
        lines.extend(_indent_lines((_decode_log_text(match.group("content")).splitlines() or [""]), prefix="      "))

    return lines


def _extract_single_block(pattern: re.Pattern[str], message: str) -> str | None:
    match = pattern.search(message)
    if not match:
        return None
    return _decode_log_text(match.group("content"))


def _format_jsonish(value: str) -> str:
    text = value.strip()
    if text.startswith("{") or text.startswith("["):
        try:
            return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return value
    return value


def _decode_log_text(value: str) -> str:
    return (
        value.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\\"", '"')
        .replace("\\'", "'")
    )


def _indent_lines(lines: list[str], prefix: str = "  ") -> list[str]:
    return [f"{prefix}{line}" if line else prefix.rstrip() for line in lines]
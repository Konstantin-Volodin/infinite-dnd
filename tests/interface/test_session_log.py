from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import RequestUsage

from src.interface.session_log import Logger, _digest_message, list_logs, load_session


def _write_session(tmp_path) -> None:
    logger = Logger(character_id="hero", max_turns=3, scenario="demo", scenario_title="Demo Quest", log_dir=tmp_path)
    logger.log_turn(1)
    with logger.run("character:hero"):
        logger.log_messages("character:hero", [
            ModelRequest(parts=[SystemPromptPart(content="you are hero"), UserPromptPart(content="act")]),
            ModelResponse(
                parts=[ToolCallPart(tool_name="speak", args='{"message": "hi"}', tool_call_id="t1")],
                usage=RequestUsage(input_tokens=10, output_tokens=5),
                model_name="test-model",
            ),
            ModelRequest(parts=[ToolReturnPart(tool_name="speak", content="ok", tool_call_id="t1")]),
        ])
    logger.log_event("resolved", tool="Speak", subject="hero", result="hero says: \"hi\"")
    logger.close()


def test_roundtrip(tmp_path):
    _write_session(tmp_path)

    files = list_logs(tmp_path)
    assert len(files) == 1
    assert files[0]["character_id"] == "hero"
    assert files[0]["scenario_title"] == "Demo Quest"
    assert files[0]["turns_completed"] == 1

    session = load_session(files[0]["path"])
    assert session["summary"]["scenario_title"] == "Demo Quest"
    assert session["summary"]["turns_completed"] == 1
    assert session["stats"]["llm_message_count"] == 3
    assert session["stats"]["error_count"] == 0

    run, = session["runs"]
    assert run["label"] == "character:hero"
    assert run["tool_calls"] == ["speak"]
    assert run["tokens"] == {"input_tokens": 10, "output_tokens": 5}
    assert run["elapsed_s"] is not None

    request, response, tool_return = [e for e in session["entries"] if e["event"] == "llm_message"]
    assert request["message_kind"] == "model_request"
    assert "you are hero" in request["raw_pretty"]
    assert response["message_kind"] == "model_response"
    assert response["tool_calls"] == ["speak"]
    assert response["usage"] == {"input_tokens": 10, "output_tokens": 5}
    assert tool_return["message_kind"] == "tool_return"
    assert tool_return["tool_returns"] == ["speak"]


def test_digest_legacy_repr_string():
    message = (
        "ModelResponse(parts=[ToolCallPart(tool_name='travel', args='{}', tool_call_id='x')], "
        "usage=RequestUsage(input_tokens=42, cache_read_tokens=7, output_tokens=3), model_name='m')"
    )
    digest = _digest_message(message)
    assert digest["kind"] == "model_response"
    assert digest["tool_calls"] == ["travel"]
    assert digest["usage"] == {"input_tokens": 42, "cache_read_tokens": 7, "output_tokens": 3}

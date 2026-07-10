from src.agents.server import _performance_args, _reasoning_args, _speculative_args


def test_gemma_4_reasoning_off_uses_tool_safe_zero_budget(monkeypatch):
    monkeypatch.setenv("LLM_REASONING", "off")

    assert _reasoning_args("unsloth/gemma-4-26B-A4B-it-GGUF") == [
        "--reasoning",
        "auto",
        "--reasoning-budget",
        "0",
    ]


def test_other_models_keep_reasoning_off(monkeypatch):
    monkeypatch.setenv("LLM_REASONING", "off")

    assert _reasoning_args("qwen3.5-35b") == ["--reasoning", "off"]


def test_explicit_gemma_4_reasoning_mode_is_preserved(monkeypatch):
    monkeypatch.setenv("LLM_REASONING", "on")

    assert _reasoning_args("gemma-4-26b") == ["--reasoning", "on"]


def test_performance_defaults_cap_threads_and_offload_eleven_moe_layers(monkeypatch):
    monkeypatch.delenv("LLM_THREADS", raising=False)
    monkeypatch.delenv("LLM_THREADS_BATCH", raising=False)
    monkeypatch.delenv("LLM_N_CPU_MOE", raising=False)
    monkeypatch.setattr("src.agents.server.os.cpu_count", lambda: 12)

    assert _performance_args() == [
        "--threads", "8",
        "--threads-batch", "8",
        "--n-cpu-moe", "11",
    ]


def test_performance_defaults_are_environment_overridable(monkeypatch):
    monkeypatch.setenv("LLM_THREADS", "4")
    monkeypatch.setenv("LLM_THREADS_BATCH", "6")
    monkeypatch.setenv("LLM_N_CPU_MOE", "9")

    assert _performance_args() == [
        "--threads", "4",
        "--threads-batch", "6",
        "--n-cpu-moe", "9",
    ]


def test_speculative_mtp_args_support_embedded_drafter(monkeypatch):
    monkeypatch.setenv("LLM_SPEC_TYPE", "draft-mtp")
    monkeypatch.setenv("LLM_SPEC_DRAFT_N_MAX", "3")
    monkeypatch.delenv("LLM_SPEC_DRAFT_MODEL", raising=False)

    assert _speculative_args() == ["--spec-type", "draft-mtp", "--spec-draft-n-max", "3"]


def test_speculative_mtp_args_support_separate_drafter(monkeypatch):
    monkeypatch.setenv("LLM_SPEC_TYPE", "draft-mtp")
    monkeypatch.setenv("LLM_SPEC_DRAFT_MODEL", "mtp.gguf")

    assert _speculative_args() == [
        "--spec-type", "draft-mtp",
        "--spec-draft-n-max", "3",
        "--spec-draft-model", "mtp.gguf",
    ]


def test_speculative_decoding_is_disabled_without_compatible_model(monkeypatch):
    monkeypatch.setenv("LLM_SPEC_TYPE", "none")

    assert _speculative_args() == []

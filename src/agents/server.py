"""Manages a local llama.cpp server subprocess."""

import os
import subprocess
import time
import logging
import urllib.error
import urllib.parse
import urllib.request
from dotenv import load_dotenv
load_dotenv()


def _reasoning_args(model: str) -> list[str]:
    """Build llama.cpp reasoning flags, including its Gemma 4 tool-call workaround."""
    reasoning = os.getenv("LLM_REASONING", "auto")
    if reasoning == "off" and "gemma-4" in model.lower():
        # With Gemma 4, --reasoning off makes llama.cpp emit an empty `start`
        # production in its tool-call grammar. Keeping the parser enabled with
        # a zero-token budget disables thinking without breaking that grammar.
        return ["--reasoning", "auto", "--reasoning-budget", "0"]
    return ["--reasoning", reasoning]


def _performance_args() -> list[str]:
    """Defaults measured for the local MoE model, while keeping every knob overridable."""
    default_threads = str(min(os.cpu_count() or 1, 8))
    return [
        "--threads", os.getenv("LLM_THREADS", default_threads),
        "--threads-batch", os.getenv("LLM_THREADS_BATCH", default_threads),
        "--n-cpu-moe", os.getenv("LLM_N_CPU_MOE", "11"),
    ]


def _speculative_args() -> list[str]:
    """Enable speculative decoding when a compatible embedded or separate drafter is configured."""
    spec_type = os.getenv("LLM_SPEC_TYPE", "none")
    if spec_type == "none":
        return []
    args = [
        "--spec-type", spec_type,
        "--spec-draft-n-max", os.getenv("LLM_SPEC_DRAFT_N_MAX", "3"),
    ]
    if draft_model := os.getenv("LLM_SPEC_DRAFT_MODEL"):
        args.extend(["--spec-draft-model", draft_model])
    return args

class LlamaServer:
    """manages a local llama-server subprocess."""

    def __init__(self):
        model = os.getenv("LLM_MODEL")
        model_path = os.getenv("LLM_MODEL_PATH")
        if not model and not model_path:
            raise RuntimeError("LLM_MODEL or LLM_MODEL_PATH must be set")
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
        port = urllib.parse.urlparse(base_url).port or 1234
        self._health_url = f"http://localhost:{port}/health"

        server_bin = os.getenv("LLM_SERVER_BIN", "llama-server")
        # -m loads a local file directly (no network); -hf resolves/downloads by repo id.
        model_arg = ["-m", model_path] if model_path else ["-hf", model]
        cmd = [
            server_bin, *model_arg, "--port", str(port),
            "--ctx-size", os.getenv("LLM_CTX_SIZE", "8192"),
            "--n-predict", os.getenv("LLM_N_PREDICT", "-1"),
            "--parallel", os.getenv("LLM_PARALLEL", "1"),
            "-ngl", os.getenv("LLM_NGL", "99"),
            *_performance_args(),
            *_speculative_args(),
            "--batch-size", os.getenv("LLM_BATCH_SIZE", "1024"),
            "--ubatch-size", os.getenv("LLM_UBATCH_SIZE", "512"),
            "--flash-attn", os.getenv("LLM_FLASH_ATTN", "on"),
            *_reasoning_args(model or model_path or ""),
            "--metrics",
            "--jinja",
            "--temp", os.getenv("LLM_TEMP", "1.0"),
            "--top-p", os.getenv("LLM_TOP_P", "0.95"),
            "--top-k", os.getenv("LLM_TOP_K", "64"),
            "--min-p", os.getenv("LLM_MIN_P", "0.01"),
            "--log-disable",
            "--repeat-penalty", os.getenv("LLM_REPEAT_PENALTY", "1.0"),
        ]
        logging.info(f"Starting LlamaServer with command: {' '.join(str(a) for a in cmd)}")
        self._process = subprocess.Popen(cmd)

        # Loads of 26B models can take 60s+ from disk; first-time HF downloads take longer.
        deadline = time.time() + 300
        while time.time() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(f"llama-server exited during startup with code {self._process.returncode}")
            try:
                urllib.request.urlopen(self._health_url, timeout=1).close()
                return
            except (urllib.error.URLError, urllib.error.HTTPError):
                time.sleep(0.5)
        self._process.terminate()
        raise RuntimeError(f"llama-server did not become healthy in 300s: {self._health_url}")

    def stop(self):
        self._process.terminate()
        self._process.wait()

    def __enter__(self): return self
    def __exit__(self, *_): self.stop()

# src/llm/core.py
"""
Handles LLM server management and model creation.
- `LlamaServer`: manages a local llama-server subprocess.
- `create_model`: factory for OpenAIChatModel from env vars.
- `ToolCall`, `ToolPlan`: structured output types for agent tool calls.
"""

import os
import subprocess
import time
import logging
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


class LlamaServer:
    """manages a local llama-server subprocess."""

    _DEFAULT_PORT = 1234
    _DEFAULT_MODEL = "Jackrong/Qwopus3.5-4B-v3-GGUF:Q8_0"

    def __init__(self):
        port = os.getenv("LLM_PORT", self._DEFAULT_PORT)
        model = os.getenv("LLM_MODEL", self._DEFAULT_MODEL)
        cmd = [
            "llama-server", "-hf", model, "--port", port,
            "--ctx-size", "20000",
            "--n-predict", "-1",
            "-ngl", "99",
            "--batch-size", "1024",
            "--ubatch-size", "512",
            "--flash-attn", "on",
            "--log-disable",
            "--cache-type-k", "q8_0",
            "--cache-type-v", "q8_0",
        ]
        logging.info(f"Starting LlamaServer with command: {' '.join(str(a) for a in cmd)}")
        self._process = subprocess.Popen(cmd)
        time.sleep(10)

    def stop(self):
        self._process.terminate()
        self._process.wait()

    def __enter__(self): return self
    def __exit__(self, *_): self.stop()


def create_model() -> OpenAIChatModel:
    """Create an OpenAIChatModel from environment variables."""
    return OpenAIChatModel(
        os.getenv("LLM_MODEL", ""),
        provider=OpenAIProvider(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:1234/v1"),
            api_key=os.getenv("LLM_API_KEY", "not-needed"),
        ),
    )


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolPlan(BaseModel):
    calls: list[ToolCall] = Field(default_factory=list)

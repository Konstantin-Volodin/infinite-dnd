# src/llm/core.py
"""
Handles LLM server management and client interactions.
- `LlamaServer`: manages a local llama-server subprocess.
- `LLMClient`: wrapper for making synchronous LLM requests with structured output support.
"""

import os
import subprocess
import time
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


class LlamaServer:
    """manages a local llama-server subprocess."""

    _DEFAULT_PORT = 1234
    _DEFAULT_MODEL = "Jackrong/Qwopus3.5-4B-v3-GGUF:Q8_0"
    _DEFAULT_CTX_SIZE = "30000"
    _DEFAULT_N_PREDICT = "-1"

    def __init__(self):
        port = os.getenv("LLM_PORT", self._DEFAULT_PORT)
        model = os.getenv("LLM_MODEL", self._DEFAULT_MODEL)
        ctx = os.getenv("LLAMA_CTX_SIZE", self._DEFAULT_CTX_SIZE)
        n_predict = os.getenv("LLAMA_N_PREDICT", self._DEFAULT_N_PREDICT)
        ngl = os.getenv("LLAMA_N_GPU_LAYERS", "99")
        
        cmd = ["llama-server", "-hf", model, "--port", port, "--ctx-size", ctx, "--n-predict", n_predict, "-ngl", ngl, "--log-disable"]
        logging.info(f"Starting LlamaServer with command: {' '.join(cmd)}")
        self._process = subprocess.Popen(cmd)
        time.sleep(10)

    def stop(self):
        self._process.terminate()
        self._process.wait()

    def __enter__(self): return self
    def __exit__(self, *_): self.stop()


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolPlan(BaseModel):
    calls: list[ToolCall] = Field(default_factory=list)


OutputT = TypeVar("OutputT")


class LLMClient:
    """Thin wrapper for synchronous LLM requests."""

    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
        self.api_key = os.getenv("LLM_API_KEY", "not-needed")
        self.model_name = os.getenv("LLM_MODEL", "")

        if not self.model_name:
            raise ValueError("LLM_MODEL must be set")

        self.model = OpenAIChatModel(
            self.model_name,
            provider=OpenAIProvider(base_url=self.base_url, api_key=self.api_key),
        )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        output_type: type[OutputT] = str,
    ) -> OutputT:
        agent = Agent(self.model, instructions=system_prompt, output_type=output_type)
        result = agent.run_sync(user_prompt)
        return result.output

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        return self.complete(system_prompt, user_prompt, output_type=str)

    def plan(self, system_prompt: str, user_prompt: str) -> ToolPlan:
        return self.complete(system_prompt, user_prompt, output_type=ToolPlan)


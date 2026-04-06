"""Minimal synchronous LLM client built on PydanticAI."""

import os
from typing import Any, TypeVar

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


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
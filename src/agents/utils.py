
import os

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

def create_model() -> Model:
    """Create a Model from environment variables.

    LLM_PROVIDER=anthropic uses the Claude API (ANTHROPIC_API_KEY); anything
    else (default) uses the local OpenAI-compatible llama.cpp server.
    """
    if os.getenv("LLM_PROVIDER", "local") == "anthropic":
        return AnthropicModel(
            os.getenv("LLM_MODEL", "claude-haiku-4-5"),
            provider=AnthropicProvider(),
        )
    return OpenAIChatModel(
        os.getenv("LLM_MODEL", ""),
        provider=OpenAIProvider(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:1234/v1"),
            api_key=os.getenv("LLM_API_KEY", "not-needed"),
        ),
    )

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

def render(template_path: str, **kwargs) -> str:
    """Render a Jinja2 template relative to src/agents/."""
    return _env.get_template(template_path).render(**kwargs).strip()

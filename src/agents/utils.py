
import os

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

def create_model() -> OpenAIChatModel:
    """Create an OpenAIChatModel from environment variables."""
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

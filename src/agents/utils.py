
import os
import urllib.parse

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.openai import OpenAIProvider


def _is_deepseek_url(base_url: str) -> bool:
    return urllib.parse.urlparse(base_url).hostname == "api.deepseek.com"


def create_model() -> OpenAIChatModel:
    """Create an OpenAIChatModel from environment variables."""
    model = os.getenv("LLM_MODEL", "")
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
    api_key = os.getenv("LLM_API_KEY", "not-needed")

    if _is_deepseek_url(base_url):
        return OpenAIChatModel(
            model,
            provider=DeepSeekProvider(api_key=api_key),
            settings={"extra_body": {"thinking": {"type": "disabled"}}},
        )

    return OpenAIChatModel(
        model,
        provider=OpenAIProvider(
            base_url=base_url,
            api_key=api_key,
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

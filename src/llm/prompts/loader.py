# src/llm/prompts/loader.py
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template_path: str, **kwargs) -> str:
    """Render a Jinja2 template relative to src/llm/prompts/."""
    return _env.get_template(template_path).render(**kwargs).strip()

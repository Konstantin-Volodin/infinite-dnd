"""Jinja2 template loader for prompt templates."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_DIR = Path(__file__).parent

_env = Environment(
    loader=FileSystemLoader(_PROMPTS_DIR),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template_path: str, **kwargs: object) -> str:
    """Render a .jinja template relative to src/prompts/.

    Example: render("character/system.jinja", char=char)
    """
    return _env.get_template(template_path).render(**kwargs).strip()

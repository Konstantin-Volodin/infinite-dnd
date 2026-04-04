"""Dungeon Master prompts — system prompt and context builder."""

from .system import build_dm_system_prompt
from .context import build_dm_context

__all__ = [
    "build_dm_system_prompt",
    "build_dm_context",
]

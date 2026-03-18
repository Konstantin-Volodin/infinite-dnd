"""
Prompts module - System prompts and context builders for agents.

Each agent type has:
- SYSTEM_PROMPT: The static instructions for the agent
- build_*_system_prompt(): Returns the system prompt
- build_*_context(): Builds dynamic context from world state
"""

from .dm import build_dm_system_prompt, build_dm_context
from .character import (
    build_character_system_prompt,
    build_character_context,
    build_casting_system_prompt,
    build_casting_context,
)

__all__ = [
    "build_dm_system_prompt",
    "build_dm_context",
    "build_character_system_prompt",
    "build_character_context",
    "build_casting_system_prompt",
    "build_casting_context",
]

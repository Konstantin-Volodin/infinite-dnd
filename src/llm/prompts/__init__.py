# src/llm/prompts/__init__.py
"""
Prompts module - system prompts and context builders for agents.

Each agent type has:
- build_*_system_prompt(): Returns the system prompt
- build_*_context(): Builds dynamic context from world state
"""

from .dungeon_master.build import build_dm_system_prompt, build_dm_context
from .character.build import build_character_system_prompt, build_character_context
from .director.build import build_director_system_prompt, build_director_context

__all__ = [
    "build_dm_system_prompt",
    "build_dm_context",
    "build_character_system_prompt",
    "build_character_context",
    "build_director_system_prompt",
    "build_director_context",
]

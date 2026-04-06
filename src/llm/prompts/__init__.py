# src/llm/prompts/__init__.py
"""
Prompts module - system prompts and context builders for agents.

Each agent type has:
- build_*_system_prompt(): Returns the system prompt
- build_*_context(): Builds dynamic context from world state
"""

from .dungeon_master.build import dm_system, dm_context
from .character.build import character_system, character_context
from .director.build import director_system, director_context

__all__ = [
    "dm_system",
    "dm_context",
    "character_system",
    "character_context",
    "director_system",
    "director_context",
]

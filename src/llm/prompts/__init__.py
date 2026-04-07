# src/llm/prompts/__init__.py
"""
Prompts module - system prompts and context builders for agents.

Each agent type has:
- A system prompt that defines their identity, role, and behavior guidelines.
- A context builder that takes the current world state and formats it into a prompt to inform the agent's decisions.
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
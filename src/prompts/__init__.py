"""
Prompts module - System prompts and context builders for agents.

Each agent type has:
- SYSTEM_PROMPT: The static instructions for the agent
- build_*_system_prompt(): Returns the system prompt
- build_*_context(): Builds dynamic context from world state
"""

from .director import build_director_system_prompt, build_director_context
from .dm import build_dm_system_prompt, build_dm_context
from .character import build_character_system_prompt, build_character_context
from .storyteller import build_storyteller_system_prompt, build_storyteller_context

__all__ = [
    "build_director_system_prompt",
    "build_director_context",
    "build_dm_system_prompt",
    "build_dm_context",
    "build_character_system_prompt",
    "build_character_context",
    "build_storyteller_system_prompt",
    "build_storyteller_context",
]

"""
Infinite D&D - AI-driven roleplaying game.

This package provides the modular game engine with:
- core/: Data models, state management, LLM client
- agents/: DM and Character agents
- prompts/: System prompts and context builders
- tools/: Tool definitions for agents
- engine/: Game loop, actions, and logging
"""

from .engine import Engine
from .agents import DMAgent, CharacterAgent
from .core import WorldState, StateManager, LLMClient

__all__ = [
    "Engine",
    "DMAgent",
    "CharacterAgent",
    "WorldState",
    "StateManager",
    "LLMClient",
]

"""
Infinite D&D - AI-driven roleplaying game.

This package provides the modular game engine with:
- core/: Data models, state management, game engine
- agents/: DM and Character agents
- prompts/: System prompts and context builders
- tools/: Tool definitions for agents
- llm/: LLM integration, agents, prompts, and tools
"""

from .core import Engine
from .llm.agents import DMAgent, CharacterAgent
from .core import WorldState, StateManager, LLMClient

__all__ = [
    "Engine",
    "DMAgent",
    "CharacterAgent",
    "WorldState",
    "StateManager",
    "LLMClient",
]

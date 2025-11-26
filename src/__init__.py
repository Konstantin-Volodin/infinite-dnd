"""
Infinite D&D - AI-driven roleplaying game.

This package provides the modular game engine with:
- core/: Data models, state management, LLM client
- agents/: DM, Character, and Orchestrator agents
- prompts/: System prompts and context builders
- tools/: Tool definitions for agents
- engine/: Game loop, actions, and logging
"""

from .engine import Engine
from .agents import DMAgent, CharacterAgent, OrchestratorAgent
from .core import WorldState, StateManager, LLMClient

__all__ = [
    "Engine",
    "DMAgent",
    "CharacterAgent",
    "OrchestratorAgent",
    "WorldState",
    "StateManager",
    "LLMClient",
]
# src/llm/__init__.py
"""
LLM module - integration of language model agents for D&D gameplay.

Generates 4 agents that utilize a shared LLM backend to perform different roles in the game:
- CharacterAgent: impersonates individual characters, making decisions and speaking in-character.
- DungeonMasterAgent: narrates the world, introduces novelty (new locations, NPCs).
- DirectorAgent: chooses which character acts next and directs their actions.
- ActionResolverAgent: converts character actions into mechanical world-state changes.
"""

"""LLM integration package."""

from .server import LlamaServer
from .character.agent import agent as CharacterAgent
from .director.agent import agent as DirectorAgent
from .dungeon_master.agent import agent as DungeonMasterAgent
from .action_resolver.agent import agent as ActionResolverAgent

__all__ = [
    "LlamaServer",
    "CharacterAgent",
    "DungeonMasterAgent",
    "DirectorAgent",
    "ActionResolverAgent",
]
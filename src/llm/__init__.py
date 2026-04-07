# src/llm/__init__.py
"""
LLM module - integration of language model agents for D&D gameplay.

Generates 3 agents that utilize a shared LLM backend to perform different roles in the game:
- CharacterAgent: impersonates individual characters, making decisions and speaking in-character.
- DungeonMasterAgent: narrates the world, creates and modifies locations, NPCs, and quests, and provides overall storytelling.
- DirectorAgent: chooses which character acts next and directs their actions.
"""

"""LLM integration package."""

from .server import LlamaServer
from .character import agent as CharacterAgent
from .director import agent as DirectorAgent
from .dungeon_master import agent as DungeonMasterAgent

__all__ = [
    "LlamaServer",
    "CharacterAgent",
    "DungeonMasterAgent",
    "DirectorAgent",
]
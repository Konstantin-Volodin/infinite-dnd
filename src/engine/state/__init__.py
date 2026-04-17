"""World state models, persistence, queries, and mutation surface."""

from .loader import StateManager
from .models import Character, CharacterStats, HistoryEvent, Location, Quest, WorldState
from .operations import WorldOperations
from .queries import (
    characters_in_location,
    connected_location_ids,
    resolve_character,
    resolve_location_id,
    slugify,
)

__all__ = [
    "StateManager",
    "WorldOperations",
    "WorldState",
    "Character",
    "CharacterStats",
    "HistoryEvent",
    "Location",
    "Quest",
    "characters_in_location",
    "connected_location_ids",
    "resolve_character",
    "resolve_location_id",
    "slugify",
]

"""Engine package for world models, queries, mutations, and persistence."""

from .history import add_history
from .interactions import action, speak, travel, wait
from .models import (
    WorldState,
    Character,
    HistoryEvent,
    Location,
    CharacterStats,
    Quest,
)
from .queries import (
    characters_in_location,
    connected_location_ids,
    default_anchor_location,
    resolve_character,
    resolve_location_id,
    resolve_quest,
)
from .state import StateManager
from .world import (
    add_location_feature,
    adjust_hit_points,
    create_item,
    discover_location,
    drop_item,
    narrate,
    remember,
    remove_npc,
    spawn_npc,
    take_item,
    update_location,
    update_quest_status,
)

__all__ = [
    "WorldState",
    "Character",
    "HistoryEvent",
    "Location",
    "CharacterStats",
    "Quest",
    "StateManager",
    "add_history",
    "action",
    "speak",
    "travel",
    "wait",
    "characters_in_location",
    "connected_location_ids",
    "default_anchor_location",
    "resolve_character",
    "resolve_location_id",
    "resolve_quest",
    "add_location_feature",
    "adjust_hit_points",
    "create_item",
    "discover_location",
    "drop_item",
    "narrate",
    "remember",
    "remove_npc",
    "spawn_npc",
    "take_item",
    "update_location",
    "update_quest_status",
]

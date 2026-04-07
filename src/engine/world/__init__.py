"""World-state helpers, queries, interactions, and mutations."""

from .history import add_history
from .interactions import action, speak, travel, wait
from .mutations import (
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
from .queries import (
    characters_in_location,
    connected_location_ids,
    default_anchor_location,
    resolve_character,
    resolve_location_id,
    resolve_quest,
)

__all__ = [
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
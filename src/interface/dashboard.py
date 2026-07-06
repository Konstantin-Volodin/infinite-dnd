"""Local web dashboard for world-state snapshots: characters, quests, locations, and history per tick."""

from __future__ import annotations

from src.interface.assets import read_asset

_HTML = read_asset("templates/world.html")

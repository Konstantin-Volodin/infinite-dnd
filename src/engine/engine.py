"""Main game engine - coordinates action execution and state management."""

import os
import re
import warnings
from datetime import datetime
from typing import Any, Dict
from ..core.state import StateManager
from ..core.models import WorldState
from .actions import ActionExecutor


class Engine:
    """Core game engine that executes tools/actions and manages game state."""

    def __init__(self):
        """Initialize the game engine."""
        
        # Load or initialize state manager
        self.state_manager = StateManager()
        self.state: WorldState = self.state_manager.generate_state()

        # Initialize action executor
        self._actions = ActionExecutor(
            state=self.state,
            save_state=self.save_state,
            save_history=self.save_history,
        )

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _slugify(self, text: str) -> str:
        """Converts a string to a URL-friendly slug."""
        if not text: return ""
        s = text.strip().lower().replace("_", " ")
        s = re.sub(r"[^a-z0-9\s\-]", "", s)
        s = re.sub(r"\s+", "-", s)
        s = re.sub(r"-+", "-", s)
        s = s.strip("-")
        return s

    def save_state(self):
        """Save the current game state."""
        self.state_manager.save_state(self.state)

    def resolve_location_id(self, raw_location: str) -> str:
        """Resolve an LLM-provided location identifier to a known location id.

        Accepts id variants (hyphen/underscore/spacing) and name-like inputs.
        Returns the original input if no match is found.
        """
        # null check
        if not raw_location: return raw_location
        locations = self.state.locations

        # Exact match
        if raw_location in locations: return raw_location

        # Slug match
        normalized = self._slugify(raw_location)
        if normalized in locations: return normalized

        warnings.warn(f"Could not resolve location '{raw_location}' to a known ID.")
        return raw_location


    def save_history(self, text: str):
        """Add to state history, keeping last 50 events for richer context."""
        # Truncate overly long entries to protect context window
        if len(text) > 1000:
            text = text[:1000] + "...(truncated)"
        
        self.state.history.append(text)
        if len(self.state.history) > 50:
            self.state.history.pop(0)
        self.save_state()

    def advance_time(self):
        """Advance game time."""
        self.state.time += 1
        self.save_state()

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name, routing to the appropriate handler."""
        # Map tool names to methods (remove 'tool_' prefix pattern)
        method = getattr(self._actions, tool_name, None)
        if not method:
            # Try with underscores (e.g., dm_action)
            method = getattr(self._actions, tool_name.replace("-", "_"), None)

        if not method:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        # Build args based on tool type
        args = kwargs.copy()

        # Normalize location fields to 'location' and resolve IDs
        potential_location_keys = ["location", "location_id", "to_location", "target_location"]
        resolved_location = None
        
        for key in potential_location_keys:
            if key in args and isinstance(args[key], str):
                resolved_location = self.resolve_location_id(args[key])
                break
        
        # Also clean up anchor location
        resolved_anchor = None
        if "anchor_location" in args:
            resolved_anchor = self.resolve_location_id(args["anchor_location"])
        elif "anchor_location_id" in args:
             resolved_anchor = self.resolve_location_id(args["anchor_location_id"])

        # Inject standardized keys if found
        if resolved_location:
            args["location"] = resolved_location
        if resolved_anchor:
            args["anchor_location"] = resolved_anchor

        # Handle a few normalized special cases using a small dispatch map
        def _narrate(a):
            return method(a.get("content") or a.get("narration") or a.get("text") or "")

        def _create_location(a):
            # Prioritize 'location' (resolved ID), create from name if missing
            loc_id = a.get("location") or (
                a.get("name", "").lower().replace(" ", "-") if a.get("name") else ""
            )
            conn = a.get("connected_to")
            if isinstance(conn, str):
                conn = [conn]
            conn_list = [self.resolve_location_id(c) for c in (conn or []) if c]
            
            return method(
                location=loc_id, 
                name=a.get("name", ""), 
                description=a.get("description", ""), 
                connected_to=conn_list, 
                anchor_location=a.get("anchor_location")
            )

        def _create_item(a):
            return method(a.get("item_name", ""), a.get("location", ""))

        def _spawn_npc(a):
            return method(
                npc_id=a.get("npc_id", ""), 
                name=a.get("name", ""), 
                role=a.get("role", ""), 
                location=a.get("location", ""), 
                description=a.get("description", ""), 
                goal=a.get("goal", "")
            )

        def _remove_npc(a):
            return method(a.get("npc_id", ""), a.get("reason", ""))

        special = {
            "narrate": _narrate,
            "create_location": _create_location,
            "create_item": _create_item,
            "spawn_npc": _spawn_npc,
            "remove_npc": _remove_npc,
        }

        if tool_name in special:
            return special[tool_name](args)

        # Generic fallback for any other tool (like the new character tools)
        # We pass all kwargs as arguments to the method, but filter out 'tool' keys
        # This assumes the method signature matches the kwargs provided
        try:
            clean_args = {
                k: v for k, v in args.items() if k not in ["tool", "tool_name"]
            }
            return method(**clean_args)
        except TypeError as e:
            return {
                "status": "error",
                "message": f"Argument mismatch for tool {tool_name}: {e}",
            }
        except Exception as e:
            return {"status": "error", "message": f"Error executing {tool_name}: {e}"}

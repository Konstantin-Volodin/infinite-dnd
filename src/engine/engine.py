"""Main game engine - coordinates action execution and state management."""

import warnings
from typing import Any, Dict
from ..core.state import StateManager
from ..core.models import WorldState, HistoryEvent
from ..core.utils import slugify
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
        normalized = slugify(raw_location)
        if normalized in locations: return normalized

        warnings.warn(f"Could not resolve location '{raw_location}' to a known ID.")
        return raw_location


    def save_history(self, text: str, location: str):
        """Add to state history, tagging characters at the event location."""
        if len(text) > 1000:
            text = text[:1000] + "...(truncated)"

        characters = [c.id for c in self.state.characters.values() if c.location == location]
        event = HistoryEvent(text=text, location=location, characters=characters)
        self.state.history.append(event)
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

        # Normalize narrate content aliases
        if tool_name == "narrate":
            content = args.get("content") or args.get("narration") or args.get("text") or ""
            location = args.get("location", "")
            return method(content, location=location)

        # Normalize connected_to for create_location
        if tool_name == "create_location":
            conn = args.get("connected_to")
            if isinstance(conn, str):
                conn = [conn]
            args["connected_to"] = [self.resolve_location_id(c) for c in (conn or []) if c]
            if not args.get("location") and args.get("name"):
                args["location"] = args["name"].lower().replace(" ", "-")

        # Generic dispatch: pass all kwargs to the method, filtering out 'tool' keys
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

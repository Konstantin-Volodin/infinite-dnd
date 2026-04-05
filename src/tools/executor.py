"""Tool dispatch — routes tool names to ActionExecutor methods with normalization."""

import warnings
from typing import Any, Dict
from ..core.models import WorldState
from ..core.utils import slugify
from .actions import ActionExecutor


class ToolExecutor:
    """Wraps ActionExecutor with dispatch, argument normalization, and location resolution."""

    def __init__(self, state: WorldState, save_state, save_history):
        self.state = state
        self._actions = ActionExecutor(state, save_state, save_history)

    def resolve_location_id(self, raw_location: str) -> str:
        """Resolve an LLM-provided location string to a known location id."""
        if not raw_location:
            return raw_location
        locations = self.state.locations
        if raw_location in locations:
            return raw_location
        normalized = slugify(raw_location)
        if normalized in locations:
            return normalized
        warnings.warn(f"Could not resolve location '{raw_location}' to a known ID.")
        return raw_location

    def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name, routing to the appropriate ActionExecutor method."""
        method = getattr(self._actions, tool_name, None)
        if not method:
            method = getattr(self._actions, tool_name.replace("-", "_"), None)
        if not method:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        args = kwargs.copy()

        # Resolve location fields
        for key in ["location", "location_id", "to_location", "target_location"]:
            if key in args and isinstance(args[key], str):
                args["location"] = self.resolve_location_id(args[key])
                break

        if "anchor_location" in args:
            args["anchor_location"] = self.resolve_location_id(args["anchor_location"])
        elif "anchor_location_id" in args:
            args["anchor_location"] = self.resolve_location_id(args.pop("anchor_location_id"))

        # Normalize narrate aliases
        if tool_name == "narrate":
            content = args.get("content") or args.get("narration") or args.get("text") or ""
            return method(content, location=args.get("location", ""))

        # Normalize connected_to for create_location
        if tool_name == "create_location":
            conn = args.get("connected_to")
            if isinstance(conn, str):
                conn = [conn]
            args["connected_to"] = [self.resolve_location_id(c) for c in (conn or []) if c]
            if not args.get("location") and args.get("name"):
                args["location"] = args["name"].lower().replace(" ", "-")

        try:
            clean_args = {k: v for k, v in args.items() if k not in ["tool", "tool_name"]}
            return method(**clean_args)
        except TypeError as e:
            return {"status": "error", "message": f"Argument mismatch for tool {tool_name}: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Error executing {tool_name}: {e}"}

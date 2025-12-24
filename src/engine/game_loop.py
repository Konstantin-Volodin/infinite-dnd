"""Main game engine - coordinates action execution and state management."""
import os
from datetime import datetime
from typing import Any, Dict
from ..core.state import StateManager
from ..core.models import WorldState
from .actions import ActionExecutor


class Engine:
    """Core game engine that executes tools/actions and manages game state."""
    
    def __init__(self, state_path: str = "world-state/world-state.json", session_dir: str = None):
        self.state_manager = StateManager()
        self.state: WorldState = self.state_manager.load_state()
        
        # Setup logging
        log_dir = session_dir or "logs"
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M")
        self.log_file = os.path.join(log_dir, f"story-{ts}.md")
        
        # Initialize action executor
        self._actions = ActionExecutor(
            state=self.state,
            save_callback=self.save_state,
            log_callback=self._log,
            history_callback=self._add_history
        )
    
    def save_state(self):
        self.state_manager.save_state(self.state)
    
    def _log(self, text: str):
        """Write to narrative log file."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                ts = datetime.now().strftime("%H:%M")
                f.write(f"**{ts}** {text}\n\n")
        except Exception:
            pass
    
    def _add_history(self, text: str):
        """Add to state history, keeping last 30 events."""
        self.state.history.append(text)
        if len(self.state.history) > 30:
            self.state.history.pop(0)
        self.save_state()
    
    def advance_time(self):
        """Advance game time."""
        self.state.time += 1
        for loc in self.state.locations.values():
            loc.environmental_effects = []
        self.save_state()
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name, routing to the appropriate handler."""
        # Backwards compat: accept old tool names and map them to current method names
        TOOL_ALIASES = {
            "attack": "combat",
            "say": "dialogue",
            "attempt_skill": "skill_check",
        }
        tool_name = TOOL_ALIASES.get(tool_name, tool_name)
        # Map tool names to methods (remove 'tool_' prefix pattern)
        method = getattr(self._actions, tool_name, None)
        if not method:
            # Try with underscores (e.g., dm_action)
            method = getattr(self._actions, tool_name.replace("-", "_"), None)
        
        if not method:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}
        
        # Build args based on tool type
        args = kwargs.copy()
        
        # Handle special cases for backwards compatibility
        if tool_name == "dm_action":
            return method(
                args.get("target_location_id"),
                {
                    "narration": args.get("narration", ""),
                    "new_location_features": [f.get("name", f) if isinstance(f, dict) else f for f in args.get("new_features", [])],
                    "new_items": [i.get("name", i) if isinstance(i, dict) else i for i in args.get("new_items", [])]
                }
            )
        elif tool_name == "narrate":
            return method(args.get("content") or args.get("narration") or args.get("text") or "")
        elif tool_name == "spawn_event":
            return method(args.get("location_id", ""), args.get("description", ""))
        elif tool_name == "create_location":
            # If location_id isn't provided, derive from name
            loc_id = args.get("location_id") or (args.get("name", "").lower().replace(" ", "-") if args.get("name") else "")
            # Normalize connected_to to a list if provided as a single string
            conn = args.get("connected_to")
            if isinstance(conn, str):
                conn = [conn]
            return method(loc_id, args.get("name", ""), args.get("description", ""), conn or [])
        elif tool_name == "create_item":
            return method(args.get("item_name", ""), args.get("location_id", ""))
        elif tool_name == "spawn_npc":
            return method(args.get("npc_id", ""), args.get("name", ""), args.get("role", ""), args.get("location_id", ""), args.get("description", ""), args.get("goal", ""))
        elif tool_name == "remove_npc":
            return method(args.get("npc_id", ""), args.get("reason", ""))
        
        # Generic fallback for any other tool (like the new character tools)
        # We pass all kwargs as arguments to the method, but filter out 'tool' keys
        # This assumes the method signature matches the kwargs provided
        try:
            clean_args = {k: v for k, v in args.items() if k not in ["tool", "tool_name"]}
            return method(**clean_args)
        except TypeError as e:
            return {"status": "error", "message": f"Argument mismatch for tool {tool_name}: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Error executing {tool_name}: {e}"}

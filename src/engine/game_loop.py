"""Main game engine - coordinates action execution and state management."""
import os
from datetime import datetime
from typing import Any, Dict
from ..core.state import StateManager
from ..core.models import WorldState
from .actions import ActionExecutor


class Engine:
    """Core game engine that executes tools/actions and manages game state."""
    
    def __init__(self, state_path: str = "world-state/world_state.json", session_dir: str = None):
        self.state_manager = StateManager()
        self.state: WorldState = self.state_manager.load_state()
        
        # Setup logging
        log_dir = session_dir or "logs"
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"story_{ts}.md")
        
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
                ts = datetime.now().strftime("%H:%M:%S")
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
        elif tool_name == "say":
            return method(args.get("character_id"), args.get("dialogue") or args.get("content", ""), args.get("target"))
        elif tool_name == "move":
            return method(args.get("character_id"), args.get("destination") or args.get("location_id", ""))
        elif tool_name == "attack":
            return method(args.get("character_id"), args.get("target", ""), args.get("weapon", "unarmed"), args.get("style", None))
        elif tool_name == "attempt_skill":
            return method(args.get("character_id"), args.get("skill", ""), args.get("action_description", ""), args.get("difficulty", None))
        elif tool_name == "examine":
            return method(args.get("character_id"), args.get("target", ""))
        elif tool_name == "pickup":
            return method(args.get("character_id"), args.get("item_name", ""))
        elif tool_name == "use":
            return method(args.get("character_id"), args.get("item_name", ""), args.get("target", ""), args.get("spell_name", None))
        elif tool_name == "wait":
            return method(args.get("character_id"), args.get("reason"))
        elif tool_name == "narrate":
            return method(args.get("text", ""))
        elif tool_name == "spawn_event":
            return method(args.get("location_id", ""), args.get("description", ""))
        elif tool_name == "create_location":
            return method(args.get("location_id", ""), args.get("name", ""), args.get("description", ""), args.get("connected_to", []))
        elif tool_name == "create_item":
            return method(args.get("item_name", ""), args.get("location_id", ""))
        elif tool_name == "spawn_npc":
            return method(args.get("npc_id", ""), args.get("name", ""), args.get("role", ""), args.get("location_id", ""), args.get("description", ""), args.get("goal", ""))
        elif tool_name == "remove_npc":
            return method(args.get("npc_id", ""), args.get("reason", ""))
        
        return {"status": "error", "message": f"Unhandled tool: {tool_name}"}

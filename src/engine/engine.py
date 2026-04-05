"""Main game engine - coordinates action execution and state management."""

from typing import Any, Dict
from ..core.state import StateManager
from ..core.models import WorldState, HistoryEvent
from ..tools.executor import ToolExecutor


class Engine:
    """Core game engine that executes tools/actions and manages game state."""

    def __init__(self):
        self.state_manager = StateManager()
        self.state: WorldState = self.state_manager.generate_state()
        self._executor = ToolExecutor(self.state, self.save_state, self.save_history)

    def save_state(self):
        self.state_manager.save_state(self.state)

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
        self.state.time += 1
        self.save_state()

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        return self._executor.execute(tool_name, **kwargs)

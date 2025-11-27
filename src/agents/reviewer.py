"""
Reviewer Agent - Summarizes a completed session with bugs, inconsistencies, and recommendations.
"""
from typing import Dict, Any
from .base import BaseAgent
from ..core.models import WorldState


class ReviewerAgent(BaseAgent):
    """Generate a session review and summary after a session completes."""

    def summarize_session(self, state: WorldState) -> Dict[str, Any]:
        """Return a structured summary including problems and recommendations.

        Uses a JSON schema to ensure the output is machine parseable.
        """
        schema = {
            "summary": {"type": "string"},
            "bugs": {"type": "array", "items": {"type": "string"}},
            "inconsistencies": {"type": "array", "items": {"type": "string"}},
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "priority_fixes": {"type": "array", "items": {"type": "string"}}
        }

        # Build context from world state for the reviewer
        lines = [f"Session Review: Turn {state.time}"]
        lines.append("\nCharacters and locations:")
        for c in state.characters.values():
            loc = state.locations.get(c.location_id)
            lines.append(f"  - {c.name} ({c.id}) at {loc.name if loc else 'unknown'}")
        lines.append("\nRecent events:")
        for e in state.history[-30:]:
            lines.append(f"  - {e}")

        context = "\n".join(lines)

        # Ask the LLM for a JSON response
        resp = self.llm.chat_json(
            system="You are a quality reviewer for AI-driven roleplaying sessions. Summarize and list bugs/inconsistencies and prioritized recommendations.",
            user=context,
            schema=schema
        )
        if resp.get("type") == "json":
            return resp["data"]
        return {"summary": "No review generated (error).", "bugs": [], "inconsistencies": [], "recommendations": [], "priority_fixes": []}

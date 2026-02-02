"""
Storyteller Agent - Drives narrative through scenes and dramatic beats.

Unlike the Director (who manages turn order), the Storyteller thinks in 
story structure: scenes, tension, reveals, and character decision points.
"""

from typing import Dict, Any, List, Optional
from .base import BaseAgent
from ..core.models import WorldState, CharacterType
from ..prompts.storyteller import build_storyteller_system_prompt, build_storyteller_context
from ..tools import get_storyteller_tools


class StorytellerAgent(BaseAgent):
    """Orchestrates the narrative through scenes and decision points."""

    def plan_scene(self, state: WorldState) -> Dict[str, Any]:
        """
        Plan the next scene beat.
        
        Returns a dict with:
        - scene_type: "dm_scene" | "decision_point" | "transition"
        - dm_guidance: Instructions for the DM to write
        - decision_for: character_id (only if scene_type == "decision_point")
        - decision_question: What the character must decide
        - context: Additional scene context
        """
        result = self._decide(
            system_prompt=build_storyteller_system_prompt(),
            context=build_storyteller_context(state),
            tools=get_storyteller_tools(),
            fallback_tool="scene",
            fallback_args={
                "scene_type": "dm_scene",
                "dm_guidance": "Continue the story naturally.",
                "dramatic_purpose": "advancement"
            },
        )
        
        # Extract the scene plan from the tool call
        tool = result.get("tool", "scene")
        
        if tool == "scene":
            return {
                "scene_type": "dm_scene",
                "dm_guidance": result.get("dm_guidance", "Advance the story."),
                "dramatic_purpose": result.get("dramatic_purpose", "advancement"),
                "context": result.get("context", ""),
                "beat_id": result.get("beat_id", ""),
            }
        elif tool == "decision_point":
            return {
                "scene_type": "decision_point",
                "decision_for": result.get("character_id", ""),
                "decision_question": result.get("question", ""),
                "dm_guidance": result.get("setup_narration", ""),
                "stakes": result.get("stakes", ""),
            }
        elif tool == "transition":
            return {
                "scene_type": "transition",
                "dm_guidance": result.get("narration", ""),
                "to_location": result.get("to_location", ""),
                "characters": result.get("characters", []),
            }
        else:
            # Fallback
            return {
                "scene_type": "dm_scene",
                "dm_guidance": "Continue the story.",
                "dramatic_purpose": "advancement",
            }

    def evaluate_pacing(self, state: WorldState) -> Dict[str, Any]:
        """
        Evaluate current story pacing and suggest adjustments.
        
        Returns hints about whether to speed up, slow down, 
        build tension, provide release, etc.
        """
        recent = state.history[-10:] if state.history else []
        
        # Simple heuristics for pacing
        dialogue_count = sum(1 for e in recent if any(w in e.lower() for w in ['said', 'says', '"', 'asked']))
        action_count = sum(1 for e in recent if any(w in e.lower() for w in ['attacked', 'moved', 'cast', 'picked', 'examined']))
        
        suggestions = []
        
        if dialogue_count > 5:
            suggestions.append("Consider more action or movement")
        if action_count > 5:
            suggestions.append("Consider a moment of reflection or dialogue")
        if len(recent) < 3:
            suggestions.append("Story is just beginning - establish the scene")
        
        # Check for unresolved tension
        tension_words = ['tense', 'danger', 'suspicious', 'hiding', 'secret']
        has_tension = any(any(w in e.lower() for w in tension_words) for e in recent[-5:])
        
        return {
            "dialogue_heavy": dialogue_count > 4,
            "action_heavy": action_count > 4,
            "has_unresolved_tension": has_tension,
            "suggestions": suggestions,
        }

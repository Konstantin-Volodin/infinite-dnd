"""
Reviewer Agent - Summarizes a completed session with bugs, inconsistencies, and recommendations.
"""

from typing import Dict, Any
from .base import BaseAgent
from ..core.models import WorldState


SCORING_RUBRIC = """
1-2 = Broken: Fundamental failures that break immersion or game logic
3-4 = Poor: Significant issues that detract from the experience
5-6 = Acceptable: Functional but unremarkable, meeting basic expectations
7-8 = Good: Engaging with minor issues, above average quality
9-10 = Excellent: Compelling, immersive, polished - exceptional quality
"""

FEW_SHOT_EXAMPLE = """
EXAMPLE OF A LOW-QUALITY SESSION (Score: 2/10):

Issues found:
- Narrative Coherence (2/10): Only DM narrated, characters never acted; repeated descriptions of same scenes with variations; new NPCs introduced without game mechanics
- Dramatic Pacing (2/10): Stagnant, no plot progression; repeated same scenes without advancing story
- Character Authenticity (2/10): Characters only used "speak" action; no distinct voices; Elara talked to herself
- World Responsiveness (1/10): Character actions had zero impact; world static and unresponsive
- Prose Quality (3/10): Repetitive phrases like "The moon hangs low"; some good atmospheric passages but undermined by repetition
"""


class ReviewerAgent(BaseAgent):
    """Generate a session review and summary after a session completes."""

    def summarize_session(self, state: WorldState, automated_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Return a structured summary with quantitative scores for guiding principles.

        Uses a JSON schema to ensure the output is machine parseable.
        Includes automated metrics to inform LLM scoring.
        
        Args:
            state: WorldState to review
            automated_metrics: Optional pre-computed automated metrics to include in review context
        """
        schema = {
            "narrative_coherence": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 1, "maximum": 10},
                    "notes": {"type": "string"},
                    "contradictions_found": {"type": "array", "items": {"type": "string"}},
                    "context_alignment_issues": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["score", "notes"],
            },
            "dramatic_pacing": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 1, "maximum": 10},
                    "notes": {"type": "string"},
                    "felt_rushed": {"type": "boolean"},
                    "felt_draggy": {"type": "boolean"},
                    "tension_curve_description": {"type": "string"},
                    "quest_progress_observations": {"type": "string"},
                },
                "required": ["score", "notes"],
            },
            "character_authenticity": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 1, "maximum": 10},
                    "notes": {"type": "string"},
                    "voice_drift_examples": {"type": "array", "items": {"type": "string"}},
                    "characters_underused": {"type": "array", "items": {"type": "string"}},
                    "characters_overused": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["score", "notes"],
            },
            "world_responsiveness": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 1, "maximum": 10},
                    "notes": {"type": "string"},
                    "consequences_felt_earned": {"type": "boolean"},
                    "missed_reaction_opportunities": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["score", "notes"],
            },
            "prose_quality": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 1, "maximum": 10},
                    "notes": {"type": "string"},
                    "show_dont_tell_violations": {"type": "array", "items": {"type": "string"}},
                    "standout_passages": {"type": "array", "items": {"type": "string"}},
                    "repetitive_phrases": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["score", "notes"],
            },
            "overall_score": {"type": "integer", "minimum": 1, "maximum": 10},
            "overall_notes": {"type": "string"},
        }

        # Build context from world state for the reviewer
        lines = [f"Session Review: Turn {state.time}", ""]
        
        # Add automated metrics if available
        if automated_metrics:
            lines.append("=== AUTOMATED METRICS ===")
            lines.append(f"Total turns: {automated_metrics.get('dramatic_pacing', {}).get('total_turns', 0)}")
            lines.append(f"Actor distribution: {automated_metrics.get('narrative_coherence', {}).get('actor_usage_distribution', {})}")
            lines.append(f"Tool usage: {automated_metrics.get('narrative_coherence', {}).get('action_type_distribution', {})}")
            lines.append(f"Consecutive repetitions: {automated_metrics.get('narrative_coherence', {}).get('consecutive_narration_repetitions', 0)}")
            lines.append(f"Location changes: {automated_metrics.get('dramatic_pacing', {}).get('location_changes', 0)}")
            lines.append(f"Character actions: {automated_metrics.get('character_authenticity', {}).get('character_action_counts', {})}")
            lines.append(f"Dialogue/action ratio: {automated_metrics.get('character_authenticity', {}).get('dialogue_to_action_ratio', 0):.2f}")
            lines.append(f"World state changes: {automated_metrics.get('world_responsiveness', {}).get('world_state_changes', 0)}")
            lines.append(f"Repetitive phrases: {automated_metrics.get('prose_quality', {}).get('most_common_phrases', [])}")
            lines.append("")
        
        lines.append("=== CHARACTERS & LOCATIONS ===")
        for c in state.characters.values():
            loc = state.locations.get(c.location)
            loc_name = loc.name if loc else 'unknown'
            lines.append(f"  - {c.name} (ID: {c.id}) at {loc_name}")
            # Support both singular `goal` and plural `goals` on Character for backwards compatibility
            goals_list = getattr(c, "goals", None)
            if goals_list:
                lines.append(f"    Goals: {', '.join(goals_list[:3])}")
            elif getattr(c, "goal", None):
                lines.append(f"    Goals: {getattr(c, 'goal')}")
        
        lines.append("\n=== QUEST STATUS ===")
        for q in state.quests.values():
            lines.append(f"  - {q.title}: {q.status}")
        
        lines.append("\n=== RECENT EVENTS (Last 50) ===")
        for e in state.history[-50:]:
            lines.append(f"  {e}")

        context = "\n".join(lines)

        # Enhanced system prompt with rubric and examples
        system_prompt = f"""You are an expert quality reviewer for AI-driven RPG sessions. Your task is to evaluate the session against 6 guiding principles using a 1-10 scoring rubric.

{SCORING_RUBRIC}

{FEW_SHOT_EXAMPLE}

EVALUATION CRITERIA:

1. NARRATIVE COHERENCE (1-10)
   - Are there contradictions in the story?
   - Do consecutive narrations repeat unnecessarily?
   - Is actor/tool usage distributed appropriately?
   - Do actions align with established context?
   - Are new NPCs properly integrated into game mechanics?

2. DRAMATIC PACING (1-10)
   - Does the tension curve rise and fall naturally?
   - Is there meaningful plot progression?
   - Are scenes varied (exploration, combat, social, revelation)?
   - Do quests advance at a reasonable pace?
   - Does the story feel rushed or draggy?

3. CHARACTER AUTHENTICITY (1-10)
   - Do characters have distinct voices and personalities?
   - Do they use diverse tools (speak, act, move, think)?
   - Are actions motivated by character goals/backstory?
   - Is dialogue distribution appropriate?
   - Do characters avoid talking to themselves awkwardly?

4. WORLD RESPONSIVENESS (1-10)
   - Do character actions create meaningful consequences?
   - Does the world react appropriately to events?
   - Do NPCs respond believably to PCs?
   - Are world state changes reflected in narration?
   - Do consequences feel earned, not arbitrary?

5. PROSE QUALITY (1-10)
   - Does narration "show" rather than "tell"?
   - Are descriptions evocative and sensory?
   - Is there variety in sentence structure and word choice?
   - Are there standout passages that immerse the reader?
   - Are repetitive phrases avoided?

Provide specific evidence and examples for each dimension. Be honest and critical - most sessions will score in the 4-7 range."""

        # Ask the LLM for a JSON response
        resp = self.llm.chat_json(
            system=system_prompt,
            user=context,
            schema=schema,
        )
        if resp.get("type") == "json":
            return resp["data"]
        return {
            "overall_score": 0,
            "overall_notes": "No review generated (error).",
            "narrative_coherence": {"score": 0, "notes": "Error generating review"},
            "dramatic_pacing": {"score": 0, "notes": "Error generating review"},
            "character_authenticity": {"score": 0, "notes": "Error generating review"},
            "world_responsiveness": {"score": 0, "notes": "Error generating review"},
            "prose_quality": {"score": 0, "notes": "Error generating review"},
        }

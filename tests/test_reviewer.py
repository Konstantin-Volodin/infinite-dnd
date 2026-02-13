from src.core.models import WorldState, Location, Character
from src.agents.reviewer import ReviewerAgent


class DummyLLM:
    def chat_json(self, system=None, user=None, schema=None):
        return {
            "type": "json",
            "data": {
                "overall_score": 5,
                "overall_notes": "ok",
                "narrative_coherence": {"score": 5, "notes": "ok"},
                "dramatic_pacing": {"score": 5, "notes": "ok"},
                "character_authenticity": {"score": 5, "notes": "ok"},
                "world_responsiveness": {"score": 5, "notes": "ok"},
                "prose_quality": {"score": 5, "notes": "ok"},
            },
        }


def test_summarize_session_handles_location_name():
    state = WorldState()
    state.locations = {"valley-bridge": Location(id="valley-bridge", name="Valley Bridge")}
    state.characters = {"elara": Character(id="elara", name="Elara", location="valley-bridge")}

    reviewer = ReviewerAgent()
    reviewer.llm = DummyLLM()

    result = reviewer.summarize_session(state)
    assert isinstance(result, dict)
    assert "overall_score" in result

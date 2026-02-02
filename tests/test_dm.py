"""
Test DM Agent - Verify world manipulation and narration.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.models import WorldState, Character, CharacterStats, Location, NarrativeState
from src.agents.dm import DMAgent
from tests.base_test import BaseTestCase

class TestDMAgent(BaseTestCase):
    
    def setUp(self):
        self.agent = DMAgent()
        
        # Create a basic world state
        self.state = WorldState(
            narrative=NarrativeState(scene_type="exploration", tension="low"),
            locations={
                "loc-1": Location(id="loc-1", name="Ancient Crypt", description="A dusty crypt.")
            },
            characters={
                "char-1": Character(
                    id="char-1", name="Explorer", type="pc", race="Elf", class_name="Rogue",
                    backstory="Looking for treasure.", stats=CharacterStats(hp=10, max_hp=10, ac=12),
                    location="loc-1"
                )
            },
            history=[
                "Explorer entered the Ancient Crypt."
            ]
        )

    def test_examine_response(self):
        """Test if DM provides interesting details when examining."""
        print("\n--- Testing DM Examine Response ---")
        
        # Guidance simulates the engine asking for a description
        guidance = "DESCRIBE what the character finds when examining 'strange markings'. Reveal a clue about a hidden door."
        
        action = self.agent.decide_action(self.state, guidance=guidance)
        print(f"DM Action: {action}")
        
        # Expect narrate or create tool
        tools_seen = []
        if "all_calls" in action:
            tools_seen = [c["tool"] for c in action["all_calls"]]
            narration_texts = [c["arguments"].get("content") for c in action["all_calls"] if c["tool"] == "narrate"]
        else:
            tools_seen = [action.get("tool")]
            narration_texts = [action.get("content") or ""]

        self.assertTrue("narrate" in tools_seen or "create" in tools_seen)
        # Check that narration mentions 'markings' somewhere
        combined_narration = " ".join([t.lower() for t in (narration_texts or []) if t])
        if combined_narration:
            self.assertIn("marking", combined_narration)

    def test_spawn_npc_or_narrate_danger(self):
        """Test if DM can create an NPC or narrate danger when asked."""
        print("\n--- Testing DM Create NPC / Narrate Danger ---")
        
        guidance = "Something dangerous should happen! Spawn a skeleton attack."
        
        action = self.agent.decide_action(self.state, guidance=guidance)
        print(f"DM Action: {action}")
        
        # The DM could use create(type=npc) or narrate mentioning skeleton(s)
        tools_seen = []
        narration_texts = []
        if "all_calls" in action:
            tools_seen = [c["tool"] for c in action["all_calls"]]
            narration_texts = [c["arguments"].get("content") for c in action["all_calls"] if c["tool"] == "narrate"]
        else:
            tools_seen = [action.get("tool")]
            narration_texts = [action.get("content") or ""]

        # Accept create tool or narration mentioning a skeleton
        if "create" in tools_seen:
            ok = True
        else:
            narration_lower = " ".join(n.lower() for n in narration_texts if n)
            ok = ("skeleton" in narration_lower or "skeletal" in narration_lower or "danger" in narration_lower)
        self.assertTrue(ok, f"Expected create or narration mentioning skeleton. Got tools: {tools_seen}")

    def test_dm_tool_calls_with_mock(self):
        """Test that DMAgent returns tool_calls format when chat_with_tools returns calls."""
        agent = DMAgent()
        # Mock the llm client's chat_with_tools to return a tool call response
        agent.llm.chat_with_tools = lambda system, user, tools: {
            "type": "tool_calls",
            "calls": [
                {"tool": "narrate", "arguments": {"content": "A strange set of markings appears."}},
                {"tool": "create", "arguments": {"type": "item", "name": "rune", "location_id": "loc-1"}}
            ]
        }
        action = agent.decide_action(self.state, guidance="Describe markings")
        # Should include 'all_calls' and the first tool should be narrate
        self.assertEqual(action.get("tool"), "narrate")
        self.assertIn("all_calls", action)
        self.assertTrue(any(c["tool"] == "create" for c in action["all_calls"]))

if __name__ == '__main__':
    unittest.main()

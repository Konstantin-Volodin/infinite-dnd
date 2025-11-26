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
                    location_id="loc-1"
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
        
        self.assertEqual(action["tool"], "dm_action")
        self.assertIn("markings", action["narration"].lower())
        # Should ideally create a new feature or item
        self.assertTrue(len(action["new_features"]) > 0 or len(action["new_items"]) > 0)

    def test_spawn_event(self):
        """Test if DM can spawn an event when asked."""
        print("\n--- Testing DM Spawn Event ---")
        
        guidance = "Something dangerous should happen! Spawn a skeleton attack."
        
        action = self.agent.decide_action(self.state, guidance=guidance)
        print(f"DM Action: {action}")
        
        # The DM might use 'dm_action' with narration OR 'spawn_npc' depending on how it interprets it.
        # But since DMAgent.decide_action returns a structured JSON which maps to 'dm_action',
        # we expect 'dm_action' with narration describing the skeleton.
        
        self.assertEqual(action["tool"], "dm_action")
        # LLM may say "skeleton" or "skeletal" - both are valid
        narration_lower = action["narration"].lower()
        self.assertTrue(
            "skeleton" in narration_lower or "skeletal" in narration_lower,
            f"Expected 'skeleton' or 'skeletal' in narration: {action['narration']}"
        )

if __name__ == '__main__':
    unittest.main()

"""
Test Director - Verify decision making logic.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.models import WorldState, Character, CharacterStats, Location, NarrativeState
from src.agents.director import DirectorAgent
from tests.base_test import BaseTestCase

class TestDirector(BaseTestCase):
    
    def setUp(self):
        self.agent = DirectorAgent()
        
        # Create a basic world state
        self.state = WorldState(
            narrative=NarrativeState(scene_type="exploration", tension="low"),
            locations={
                "loc-1": Location(id="loc-1", name="Tavern", description="A rowdy tavern.")
            },
            characters={
                "char-1": Character(
                    id="char-1", name="Hero", type="pc", race="Human", class_name="Fighter",
                    backstory="A brave hero.", stats=CharacterStats(hp=10, max_hp=10, ac=10),
                    location="loc-1"
                ),
                "char-2": Character(
                    id="char-2", name="Villain", type="npc", race="Orc", class_name="Warrior",
                    backstory="A mean orc.", stats=CharacterStats(hp=10, max_hp=10, ac=10),
                    location="loc-1"
                )
            },
            history=[
                "Hero entered the Tavern.",
                "Villain glared at Hero."
            ]
        )

    def test_combat_transition(self):
        """Test if director handles combat scenarios."""
        print("\n--- Testing Combat Scenario ---")
        
        # Simulate a combat trigger
        self.state.history.append("Hero attacks Villain with a sword!")
        
        # Director should return a sequence of actors
        sequence = self.agent.decide_next_actors(self.state)
        print(f"Sequence: {sequence}")
        
        # Should have at least one actor in the sequence
        actors = [s.get("actor") for s in sequence]
        self.assertTrue(len(actors) > 0)

    def test_dialogue_flow(self):
        """Test if director keeps dialogue flowing."""
        print("\n--- Testing Dialogue Flow ---")
        
        self.state.history.append('Hero says: "What are you doing here?"')
        
        sequence = self.agent.decide_next_actors(self.state)
        print(f"Sequence: {sequence}")
        
        # Should have a sequence with actors
        actors = [s.get("actor") for s in sequence]
        self.assertIn("char-2", actors)

    def test_stall_detection(self):
        """Test if director detects stalling and asks DM to intervene."""
        print("\n--- Testing Stall Detection ---")
        
        # Simulate a stalled story - lots of dialogue but no progress
        self.state.history = [
            'Hero said: "Hello there."',
            'Villain said: "What do you want?"',
            'Hero said: "Just passing through."',
            'Villain said: "Then pass."',
            'Hero said: "Nice place you have here."',
            'Villain said: "Thanks."',
        ]
        
        sequence = self.agent.decide_next_actors(self.state)
        print(f"Sequence: {sequence}")
        
        # Director should return a sequence of actors
        actors = [s.get("actor") for s in sequence]
        self.assertTrue(len(actors) > 0)

if __name__ == '__main__':
    unittest.main()

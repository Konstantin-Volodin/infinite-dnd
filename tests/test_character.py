"""
Test Character Agent - Verify roleplay and decision making.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.models import WorldState, Character, CharacterStats, Location, NarrativeState
from src.agents.character import CharacterAgent
from tests.base_test import BaseTestCase

class TestCharacterAgent(BaseTestCase):
    
    def setUp(self):
        # Create a basic world state
        self.state = WorldState(
            narrative=NarrativeState(scene_type="social", tension="low"),
            locations={
                "loc-1": Location(id="loc-1", name="Tavern", description="A rowdy tavern.")
            },
            characters={
                "char-1": Character(
                    id="char-1", name="Hero", type="pc", race="Human", class_name="Fighter",
                    backstory="A brave hero looking for adventure.", stats=CharacterStats(hp=10, max_hp=10, ac=10),
                    location_id="loc-1", inventory=["sword"]
                ),
                "char-2": Character(
                    id="char-2", name="Villain", type="npc", race="Orc", class_name="Warrior",
                    backstory="A mean orc who hates heroes.", stats=CharacterStats(hp=10, max_hp=10, ac=10),
                    location_id="loc-1", inventory=["axe"]
                )
            },
            history=[
                "Hero entered the Tavern."
            ]
        )
        self.agent = CharacterAgent("char-1")

    def test_social_response(self):
        """Test if character responds to dialogue."""
        print("\n--- Testing Character Social Response ---")
        
        # Simulate someone talking to the character
        self.state.history.append('Villain says: "Get out of my tavern, weakling!"')
        
        # Provide situation context but NO direct command - Hero must decide
        guidance = "SITUATION: The Villain has just insulted the Hero in a crowded tavern."
        
        action = self.agent.decide_action(self.state, guidance=guidance)
        print(f"Character Action: {action}")
        
        self.assertEqual(action["tool"], "say")
        # The tool definition uses 'content', but the handler might map it. 
        # The raw LLM response uses 'content'.
        dialogue = action.get("dialogue") or action.get("content")
        self.assertIsNotNone(dialogue)
        # Just check that they said something substantial
        self.assertTrue(len(dialogue) > 10, "Character should respond with a sentence.")

    def test_combat_action(self):
        """Test if character attacks in combat."""
        print("\n--- Testing Character Combat Action ---")
        
        # Set scene to combat
        self.state.narrative.scene_type = "combat"
        self.state.narrative.tension = "high"
        self.state.history.append("Villain attacks Hero!")
        
        # Provide situation context but NO direct command
        guidance = "SITUATION: Combat has started. The Villain is attacking the Hero."
        
        action = self.agent.decide_action(self.state, guidance=guidance)
        print(f"Character Action: {action}")
        
        # Should attack or use an item
        self.assertIn(action["tool"], ["attack", "use"])
        if action["tool"] == "attack":
            self.assertEqual(action["target"], "Villain")

    def test_context_building(self):
        """Test character context building."""
        print("\n--- Testing Character Context Building ---")
        
        

if __name__ == '__main__':
    unittest.main()

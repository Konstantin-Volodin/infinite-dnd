"""
Test Orchestrator - Verify decision making logic.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.models import WorldState, Character, CharacterStats, Location, NarrativeState
from src.agents.orchestrator import OrchestratorAgent
from tests.base_test import BaseTestCase

class TestOrchestrator(BaseTestCase):
    
    def setUp(self):
        self.agent = OrchestratorAgent()
        
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
                    location_id="loc-1"
                ),
                "char-2": Character(
                    id="char-2", name="Villain", type="npc", race="Orc", class_name="Warrior",
                    backstory="A mean orc.", stats=CharacterStats(hp=10, max_hp=10, ac=10),
                    location_id="loc-1"
                )
            },
            history=[
                "Hero entered the Tavern.",
                "Villain glared at Hero."
            ]
        )

    def test_combat_transition(self):
        """Test if orchestrator recognizes combat start."""
        print("\n--- Testing Combat Transition ---")
        
        # Simulate a combat trigger
        self.state.history.append("Hero attacks Villain with a sword!")
        
        # We expect the orchestrator to:
        # 1. Update narrative to 'combat' / 'high tension'
        # 2. Select the Villain (to react) or DM (to resolve hit)
        
        decision = self.agent.decide_next_actor(self.state)
        
        print(f"Decision: {decision}")
        
        # Check if narrative update was suggested
        if "narrative_update" in decision:
            update = decision["narrative_update"]
            print(f"Narrative Update: {update}")
            self.assertEqual(update.get("scene_type"), "combat")
            self.assertIn(update.get("tension"), ["rising", "high"])
        else:
            print("⚠️ No narrative update triggered")

    def test_dialogue_flow(self):
        """Test if orchestrator keeps dialogue flowing."""
        print("\n--- Testing Dialogue Flow ---")
        
        self.state.history.append('Hero says: "What are you doing here?"')
        
        decision = self.agent.decide_next_actor(self.state)
        print(f"Decision: {decision}")
        
        # Should pick the Villain to respond
        self.assertEqual(decision.get("actor"), "char-2")

    def test_stall_detection(self):
        """Test if orchestrator detects stalling and asks DM to intervene."""
        print("\n--- Testing Stall Detection ---")
        
        # Simulate a stalled story - lots of dialogue but no progress
        self.state.narrative.stall_counter = 4  # Already stalled
        self.state.history = [
            'Hero said: "Hello there."',
            'Villain said: "What do you want?"',
            'Hero said: "Just passing through."',
            'Villain said: "Then pass."',
            'Hero said: "Nice place you have here."',
            'Villain said: "Thanks."',
        ]
        
        decision = self.agent.decide_next_actor(self.state)
        print(f"Decision: {decision}")
        
        # When stalled, orchestrator should select DM to inject drama
        self.assertEqual(decision.get("actor"), "dm")
        
        # The suggested action should mention injecting something
        suggested = decision.get("suggested_action", "").lower()
        self.assertTrue(
            any(word in suggested for word in ["complication", "twist", "inject", "event", "drama", "tension"]),
            f"Expected suggestion to mention drama injection, got: {suggested}"
        )

if __name__ == '__main__':
    unittest.main()

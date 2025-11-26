from src.core.models import WorldState, Character, CharacterStats, Location, NarrativeState
from src.agents.character import CharacterAgent
from tests.base_test import BaseTestCase

class TestSkillChecks(BaseTestCase):
    
    def setUp(self):
        self.state = WorldState(
            narrative=NarrativeState(scene_type="exploration", tension="low"),
            locations={
                "loc-1": Location(id="loc-1", name="Locked Room", description="A room with a locked door.")
            },
            characters={
                "char-1": Character(
                    id="char-1", name="Rogue", type="pc", race="Elf", class_name="Rogue",
                    backstory="Expert lockpicker.", stats=CharacterStats(hp=10, max_hp=10, ac=12),
                    location_id="loc-1"
                )
            },
            history=["Rogue is standing before a locked door."]
        )
        self.agent = CharacterAgent("char-1")

    def test_skill_attempt(self):
        """Test if character attempts a skill check when appropriate."""
        print("\n--- Testing Skill Check Attempt ---")
        
        # Update history to show they already looked
        self.state.history.append("Rogue examined the door. It is locked with a complex mechanism.")
        
        guidance = "SITUATION: The door is locked. You need to pick the lock to proceed."
        
        action = self.agent.decide_action(self.state, guidance=guidance)
        print(f"Character Action: {action}")
        
        self.assertEqual(action["tool"], "attempt_skill")
        self.assertIn("lock", action["action_description"].lower())
        # Allow various valid skill names
        self.assertIn(action["skill"], ["sleight_of_hand", "dexterity", "thieves_tools", "lockpicking"])

    def test_engine_resolution(self):
        """Test if the engine correctly resolves a skill check."""
        print("\n--- Testing Engine Resolution ---")
        from src.engine import Engine
        import os
        
        # Use a temp file for this test to avoid corruption issues
        temp_state_file = f"world-state/test_state_{os.getpid()}.json"
        
        # Setup engine with our state
        engine = Engine(temp_state_file) 
        engine.state = self.state
        # CRITICAL: Update references to the state in helper objects
        engine._actions.state = self.state
        
        try:
            # Execute the tool directly
            result = engine.execute_tool(
                "attempt_skill", 
                character_id="char-1", 
                skill="sleight_of_hand", 
                action_description="I pick the lock."
            )
            
            print(f"Engine Result: {result}")
            
            self.assertEqual(result["status"], "success")
            self.assertIn("roll", result)
            self.assertIn("modifier", result)
            
            # Check history for the system message
            last_event = engine.state.history[-1]
            print(f"History Event: {last_event}")
            self.assertIn("[SYSTEM]", last_event)
            self.assertIn("Sleight_Of_Hand", last_event.replace(" ", "_").title()) # Normalize for check
            
        finally:
            # Cleanup
            if os.path.exists(temp_state_file):
                os.remove(temp_state_file)

if __name__ == '__main__':
    import unittest
    unittest.main()

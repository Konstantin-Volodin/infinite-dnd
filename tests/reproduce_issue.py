import sys
import os
import json
import shutil

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.engine import Engine
from src.core.models import WorldState

def reproduce():
    print("--- Reproducing Issues ---")
    
    # 1. Setup temporary state
    original_state = "world-state/world_state.json"
    test_state = "world-state/test_state.json"
    if os.path.exists(original_state):
        shutil.copy(original_state, test_state)
    else:
        print("Original state not found, skipping Pydantic test on existing data.")
        return

    # 2. Load Engine (triggers Pydantic validation on load/save)
    print(f"Loading state from {test_state}...")
    try:
        engine = Engine(test_state, session_dir="logs/test_session")
        print("State loaded.")
    except Exception as e:
        print(f"Error loading state: {e}")
        return

    # 3. Trigger Pydantic Warning (Save State)
    print("Saving state to trigger Pydantic warning...")
    try:
        engine.save_state()
        print("State saved.")
    except Exception as e:
        print(f"Error saving state: {e}")

    # 4. Test Action Failure (Fuzzy Match)
    print("\nTesting 'examine spice stall' (expecting failure currently)...")
    # Assuming 'elara' is in 'market-square' and 'spice stall' feature exists as 'spice stall (barricade...)'
    # In the provided logs, the feature is "spice stall (barricade the stall with crates to create a distraction)"
    # But the user tried "spice stall" and it failed.
    
    char_id = "elara"
    if char_id in engine.state.characters:
        char = engine.state.characters[char_id]
        # Force location to market-square if not there
        char.location_id = "market-square"
        
        # Try examine
        result = engine.execute_tool("examine", character_id=char_id, target="spice stall")
        print(f"Result: {result}")
        
        if result.get("status") == "error" and "doesn't exist" in result.get("message", ""):
            print("FAILED: 'spice stall' still failed to match.")
        else:
            print("SUCCESS: 'spice stall' matched!")
            
    # 5. Test Combat Trigger
    print("\nTesting Combat Trigger...")
    # Attack a dummy target
    if char_id in engine.state.characters:
        # Create a dummy target
        engine.execute_tool("spawn_npc", npc_id="dummy_target", name="Dummy", role="target", location_id="market-square")
        
        # Attack
        result = engine.execute_tool("attack", character_id=char_id, target="Dummy")
        print(f"Attack Result: {result}")
        
        if engine.state.narrative.scene_type == "combat":
            print("SUCCESS: Combat state triggered.")
        else:
            print(f"FAILED: Scene type is {engine.state.narrative.scene_type}")

    # 6. Test ID Sanitization
    print("\nTesting ID Sanitization...")
    # Try to create location with bad ID
    engine.execute_tool("create_location", location_id="Bad' Location!", name="Bad Loc", description="Test")
    if "bad-location" in engine.state.locations:
        print("SUCCESS: 'Bad' Location!' sanitized to 'bad-location'")
    else:
        print(f"FAILED: Location ID not sanitized properly. Keys: {list(engine.state.locations.keys())}")

    # Cleanup
    if os.path.exists(test_state):
        os.remove(test_state)

if __name__ == "__main__":
    reproduce()

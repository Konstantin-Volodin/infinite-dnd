"""
Quick verification script for character agency features.
Tests new self-modification and world interaction tools.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.core.models import WorldState, Character, Location, CharacterType
from src.engine.actions import ActionExecutor


def test_character_agency():
    """Test new character agency features."""
    
    # Create minimal world state
    state = WorldState()
    state.locations = {
        "test-room": Location(
            id="test-room",
            name="Test Room",
            description="A simple room",
            features=["door", "candle"],
            items=["Rune Key Fragment"]
        )
    }
    
    state.characters = {
        "kael": Character(
            id="kael",
            name="Kael",
            type=CharacterType.NPC,
            class_name="thief",
            backstory="A mysterious thief",
            goal="steal the Rune Key Fragment",
            location_id="test-room"
        ),
        "elara": Character(
            id="elara",
            name="Elara",
            type=CharacterType.PC,
            class_name="former-guard",
            goal="Find her brother",
            location_id="test-room",
            inventory=["guard-pendant"]
        )
    }
    
    # Create action executor
    logs = []
    history = []
    
    def save_cb():
        pass
    
    def log_cb(msg):
        logs.append(msg)
        print(f"LOG: {msg}")
    
    def hist_cb(msg):
        history.append(msg)
    
    executor = ActionExecutor(state, save_cb, log_cb, hist_cb)
    
    print("\n=== Testing Character Agency Features ===\n")
    
    # Test 1: update_knowledge
    print("Test 1: Elara learns something")
    result = executor.update_knowledge("elara", "The Rune Key Fragment is in this room")
    print(f"Result: {result}")
    print(f"Elara's knowledge: {state.characters['elara'].knowledge}")
    assert "The Rune Key Fragment is in this room" in state.characters["elara"].knowledge
    print("✅ update_knowledge works!\n")
    
    # Test 2: reflect (change motivation)
    print("Test 2: Kael changes motivation")
    result = executor.reflect("kael", "Must acquire that key before Elara notices", "discovered the key location")
    print(f"Result: {result}")
    print(f"Kael's motivation: {state.characters['kael'].current_motivation}")
    assert state.characters["kael"].current_motivation == "Must acquire that key before Elara notices"
    print("✅ reflect works!\n")
    
    # Test 3: add_memory
    print("Test 3: Elara records a memory")
    result = executor.add_memory("elara", "Found strange runes in the market", "high")
    print(f"Result: {result}")
    print(f"Elara's memories: {state.characters['elara'].memory}")
    assert len(state.characters["elara"].memory) == 1
    print("✅ add_memory works!\n")
    
    # Test 4: steal
    print("Test 4: Kael steals the Rune Key Fragment")
    result = executor.steal("kael", "Rune Key Fragment", "from the location")
    print(f"Result: {result}")
    print(f"Kael's inventory: {state.characters['kael'].inventory}")
    assert "Rune Key Fragment" in state.characters["kael"].inventory
    assert "Rune Key Fragment" not in state.locations["test-room"].items
    print("✅ steal works!\n")
    
    # Test 5: create_small_item
    print("Test 5: Elara creates a note")
    result = executor.create_small_item("elara", "scribbled note", "map to brother's location")
    print(f"Result: {result}")
    print(f"Items in room: {state.locations['test-room'].items}")
    assert "scribbled note" in state.locations["test-room"].items
    print("✅ create_small_item works!\n")
    
    # Test 6: modify_feature
    print("Test 6: Elara barricades the door")
    result = executor.modify_feature("elara", "door", "barricaded")
    print(f"Result: {result}")
    print(f"Features: {state.locations['test-room'].features}")
    assert "door (barricaded)" in state.locations["test-room"].features
    print("✅ modify_feature works!\n")
    
    # Test 7: destroy_item
    print("Test 7: Kael destroys evidence")
    result = executor.destroy_item("kael", "Rune Key Fragment", "smashed under boot")
    print(f"Result: {result}")
    print(f"Kael's inventory: {state.characters['kael'].inventory}")
    assert "Rune Key Fragment" not in state.characters["kael"].inventory
    print("✅ destroy_item works!\n")
    
    print("=== All Tests Passed! ===")
    print(f"\nTotal log entries: {len(logs)}")
    print(f"Total history entries: {len(history)}")
    
    return True


if __name__ == "__main__":
    try:
        test_character_agency()
        print("\n✨ Character agency implementation verified!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

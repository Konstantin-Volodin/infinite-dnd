import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.prompts.director import build_director_context
from src.core.models import WorldState, NarrativeState

def test_dialogue_penalty_removed():
    # Create a state with recent dialogue
    state = WorldState(
        narrative=NarrativeState(stall_counter=0, tension="low", scene_type="social"),
        characters={},
        locations={},
        history=['Char1 says "Hello"', 'Char2 says "Hi"', 'Char1 says "How are you?"']
    )
    
    context = build_director_context(state)
    
    if "Too much dialogue recently" in context:
        print("❌ FAILED: Dialogue penalty still present in context")
        print(context)
        sys.exit(1)
    else:
        print("✅ PASSED: Dialogue penalty not found in context")

if __name__ == "__main__":
    test_dialogue_penalty_removed()

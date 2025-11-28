import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.prompts.director import build_director_context
from src.core.models import WorldState, NarrativeState

def test_stall_alert_removed():
    # Create a state with high stall counter
    state = WorldState(
        narrative=NarrativeState(stall_counter=10, tension="high", scene_type="exploration"),
        characters={},
        locations={},
        history=[]
    )
    
    context = build_director_context(state)
    
    if "STALL ALERT" in context:
        print("❌ FAILED: STALL ALERT still present in context")
        print(context)
        sys.exit(1)
    else:
        print("✅ PASSED: STALL ALERT not found in context")

if __name__ == "__main__":
    test_stall_alert_removed()

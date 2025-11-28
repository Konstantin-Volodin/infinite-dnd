import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine import Engine
from src.core.models import WorldState, NarrativeState

def test_ambush_removed():
    # Mock engine and state
    engine = MagicMock(spec=Engine)
    engine.state = WorldState(
        narrative=NarrativeState(stall_counter=0, tension="high", scene_type="exploration"),
        characters={},
        locations={},
        history=[]
    )
    
    # We need to simulate the part of run_game loop where the check happened
    # Since we can't easily import the loop function without running it, 
    # we will inspect the file content directly for the commented out code.
    
    with open("run_game.py", "r", encoding="utf-8") as f:
        content = f.read()
        
    if 'if engine.state.narrative.tension == "high" and current_focus:' in content:
        # Check if it's commented out
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if 'if engine.state.narrative.tension == "high" and current_focus:' in line:
                if not line.strip().startswith("#"):
                    print(f"❌ FAILED: Ambush logic still active at line {i+1}")
                    sys.exit(1)
        
    print("✅ PASSED: Ambush logic is commented out")

if __name__ == "__main__":
    test_ambush_removed()

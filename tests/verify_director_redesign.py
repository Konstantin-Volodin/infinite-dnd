import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools import get_director_tools

def test_director_tools():
    """Verify that director tools have been updated correctly."""
    tools = get_director_tools()
    
    tool_names = [t["function"]["name"] for t in tools]
    
    # Check that select_next_actor exists
    if "select_next_actor" not in tool_names:
        print("❌ FAILED: select_next_actor tool not found")
        sys.exit(1)
    
    # Check that update_narrative exists
    if "update_narrative" not in tool_names:
        print("❌ FAILED: update_narrative tool not found")
        sys.exit(1)
    
    # Check that plan_sequence is removed
    if "plan_sequence" in tool_names:
        print("❌ FAILED: plan_sequence should be removed but still exists")
        sys.exit(1)
    
    # Check select_next_actor has character_thinking parameter
    select_tool = next(t for t in tools if t["function"]["name"] == "select_next_actor")
    params = select_tool["function"]["parameters"]["properties"]
    
    if "character_thinking" not in params:
        print("❌ FAILED: select_next_actor missing character_thinking parameter")
        sys.exit(1)
    
    if "suggested_action" in params:
        print("❌ FAILED: select_next_actor should not have suggested_action parameter")
        sys.exit(1)
    
    print("✅ PASSED: Director tools updated correctly")
    print(f"   Tools: {', '.join(tool_names)}")

if __name__ == "__main__":
    test_director_tools()

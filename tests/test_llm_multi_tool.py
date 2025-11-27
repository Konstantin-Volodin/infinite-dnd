import pytest
import sys
import os

# Add project root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.llm import LLMClient

def test_llm_multiple_tool_calls():
    """
    Test if the LLM can generate multiple tool calls in a single response
    when the scenario demands it.
    """
    client = LLMClient()
    
    system_prompt = (
        "You are a D&D combat agent. You must be efficient. "
        "If you need to perform multiple actions to achieve a goal, "
        "use MANY tool calls in parallel. Do not wait for the first action to complete. "
        "Output all tool calls in a single response."
    )
    
    # Scenario: The enemy is 10ft away. The agent has a sword but needs to move closer to hit.
    context = (
        "You are a Fighter. You are currently 10 feet away from a Goblin. "
        "You have a Longsword equipped. Your speed is 30 feet. "
        "The Goblin is low on health. "
        "Goal: Defeat the Goblin immediately."
    )
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "move",
                "description": "Move a certain distance towards a target.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "distance_feet": {"type": "integer", "description": "Distance to move in feet"},
                        "direction": {"type": "string", "description": "Direction to move"}
                    },
                    "required": ["distance_feet"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "attack",
                "description": "Attack a target with equipped weapon. Target must be within 5 feet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Name of the target"}
                    },
                    "required": ["target"]
                }
            }
        }
    ]

    print(f"\nPrompting LLM with context: {context}")
    result = client.chat_with_tools(system_prompt, context, tools)
    
    print(f"LLM Result Type: {result.get('type')}")
    
    if result["type"] == "tool_calls":
        calls = result["calls"]
        print(f"Tool calls generated ({len(calls)}):")
        for call in calls:
            print(f" - {call['tool']}: {call['arguments']}")
            
        # We expect at least a move and an attack
        tool_names = [c['tool'] for c in calls]
        
        assert len(calls) >= 2, f"Expected multiple tool calls, got {len(calls)}"
        assert "move" in tool_names, "Expected a move action"
        assert "attack" in tool_names, "Expected an attack action"
    else:
        pytest.fail(f"LLM did not return tool calls. Returned: {result}")

if __name__ == "__main__":
    test_llm_multiple_tool_calls()

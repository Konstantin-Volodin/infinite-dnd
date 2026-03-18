"""Test DM Agent reactive behavior."""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.models import WorldState, Character, CharacterStats, Location, CharacterType
from src.agents.dm import DMAgent


class TestDMAgent(unittest.TestCase):
    def setUp(self):
        self.agent = DMAgent()
        self.state = WorldState(
            locations={
                "loc-1": Location(id="loc-1", name="Ancient Crypt", description="A dusty crypt."),
            },
            characters={
                "char-1": Character(
                    id="char-1",
                    name="Explorer",
                    type=CharacterType.PC,
                    role="rogue",
                    backstory="Looking for treasure.",
                    stats=CharacterStats(hp=10, max_hp=10),
                    location="loc-1",
                )
            },
            history=["Explorer entered the Ancient Crypt."],
        )

    def test_react_returns_tool_calls_shape(self):
        self.agent.llm.chat_with_tools = lambda system, user, tools, require_tool=False: {
            "type": "tool_calls",
            "calls": [
                {"tool": "narrate", "arguments": {"content": "Dust swirls around the old marker stones."}},
                {"tool": "create", "arguments": {"type": "item", "name": "rune shard", "description": "A chipped glowing shard.", "location": "loc-1"}},
            ],
        }

        action = self.agent.react(
            self.state,
            last_action={"character_id": "char-1", "tool": "act", "result": {"intent": "Explorer examines strange markings."}},
        )
        self.assertEqual(action.get("tool"), "narrate")
        self.assertIn("all_calls", action)
        self.assertTrue(any(c["tool"] == "create" for c in action["all_calls"]))


if __name__ == "__main__":
    unittest.main()

"""Test Character Agent casting behavior."""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.models import WorldState, Character, CharacterStats, Location, CharacterType
from src.agents.character import CharacterAgent


class TestCharacterAgent(unittest.TestCase):
    def setUp(self):
        self.state = WorldState(
            locations={
                "loc-1": Location(id="loc-1", name="Tavern", description="A rowdy tavern."),
            },
            characters={
                "char-1": Character(
                    id="char-1",
                    name="Hero",
                    type=CharacterType.PC,
                    role="fighter",
                    backstory="A brave hero looking for adventure.",
                    stats=CharacterStats(hp=10, max_hp=10),
                    location="loc-1",
                    inventory=["sword"],
                ),
                "char-2": Character(
                    id="char-2",
                    name="Villain",
                    type=CharacterType.NPC,
                    role="warrior",
                    backstory="A mean rival.",
                    stats=CharacterStats(hp=10, max_hp=10),
                    location="loc-1",
                    inventory=["axe"],
                ),
            },
            history=["Hero entered the Tavern."],
        )
        self.agent = CharacterAgent()

    def test_decide_and_act_uses_dm_prompt_when_valid(self):
        self.agent.llm.chat_with_tools = lambda system, user, tools, require_tool=False: {
            "type": "tool_calls",
            "calls": [{"tool": "speak", "arguments": {"message": "I answer at once.", "character_id": "char-1"}}],
        }
        action = self.agent.decide_and_act(self.state, dm_prompt="char-1")
        self.assertEqual(action.get("character_id"), "char-1")
        self.assertEqual(action.get("tool"), "speak")

    def test_decide_and_act_invalid_prompt_falls_back_softly(self):
        self.agent.llm.chat_with_tools = lambda system, user, tools, require_tool=False: {
            "type": "tool_calls",
            "calls": [{"tool": "think", "arguments": {"knowledge": "I observe the room."}}],
        }
        action = self.agent.decide_and_act(self.state, dm_prompt="missing-character")
        self.assertIn(action.get("character_id"), self.state.characters)
        self.assertEqual(action.get("tool"), "think")


if __name__ == "__main__":
    unittest.main()

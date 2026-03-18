import unittest
from types import SimpleNamespace

from run_game import GameRunner


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.advance_calls = 0
        self.state = SimpleNamespace(
            characters={
                "char-1": SimpleNamespace(id="char-1", location="loc-1"),
                "char-2": SimpleNamespace(id="char-2", location="loc-1"),
            },
            history=[],
            time=0,
            story_beats=[],
        )

    def execute_tool(self, tool, **kwargs):
        self.calls.append((tool, kwargs))
        return {"status": "success"}

    def advance_time(self):
        self.advance_calls += 1


class SequencedCharacter:
    def __init__(self):
        self.prompts = []

    def decide_and_act(self, state, dm_prompt=None):
        self.prompts.append(dm_prompt)
        chosen = dm_prompt if dm_prompt in state.characters else "char-1"
        return {
            "tool": "think",
            "character_id": chosen,
            "knowledge": f"{chosen} takes stock.",
        }


class PromptingDM:
    def __init__(self):
        self.turn = 0

    def react(self, state, last_action=None):
        self.turn += 1
        payload = {"tool": "narrate", "content": f"DM reacts to turn {self.turn}."}
        if self.turn == 1:
            payload["prompts_character"] = "char-2"
        elif self.turn == 2:
            payload["prompts_character"] = "missing-id"
        return payload


class PingPongLoopTests(unittest.TestCase):
    def test_pingpong_turn_order_and_soft_hint(self):
        engine = FakeEngine()
        character = SequencedCharacter()
        dm = PromptingDM()

        runner = GameRunner(
            engine,
            dm=dm,
            character=character,
            reviewer=None,
            report_generator=lambda *_: False,
        )

        runner.run_pingpong_loop(max_turns=3)

        # Character and DM both acted each turn.
        think_calls = [c for c in engine.calls if c[0] == "think"]
        narrate_calls = [c for c in engine.calls if c[0] == "narrate"]
        self.assertEqual(len(think_calls), 3)
        self.assertEqual(len(narrate_calls), 3)

        # Soft-hint: first DM hint is honored, second invalid hint is ignored.
        self.assertEqual(character.prompts[0], None)
        self.assertEqual(character.prompts[1], "char-2")
        self.assertEqual(character.prompts[2], None)


if __name__ == "__main__":
    unittest.main()

import os
import json
import tempfile
import unittest
from types import SimpleNamespace

from run_game import GameRunner


class FakeCharacterAgent:
    def __init__(self):
        self.last_prompt = None

    def decide_and_act(self, state, dm_prompt=None):
        self.last_prompt = dm_prompt
        return {
            "tool": "speak",
            "character_id": "hero",
            "message": "I have a plan.",
        }


class FakeDM:
    def react(self, state, last_action=None):
        return {
            "tool": "narrate",
            "content": "The air tightens as the party waits.",
            "prompts_character": "hero",
        }

    def generate_new_item(self, state, item, loc):
        return {"tool": "create", "type": "item", "name": item, "location": loc, "description": "Generated item"}

    def generate_new_location(self, state, target, origin):
        return {"tool": "create", "type": "location", "name": target, "location": origin, "description": "Generated location"}


class FakeReviewer:
    def summarize_session(self, state, metrics=None):
        return {"summary": "ok"}


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.state = SimpleNamespace(
            characters={"hero": SimpleNamespace(id="hero", location="loc-1")},
            history=[],
            time=0,
            story_beats=[],
        )

    def execute_tool(self, tool, **kwargs):
        self.calls.append((tool, kwargs))
        return {"status": "success"}

    def save_state(self):
        pass

    def advance_time(self):
        self.state.time += 1


class GameRunnerTests(unittest.TestCase):
    def test_execute_dm_reaction_returns_soft_hint(self):
        engine = FakeEngine()
        runner = GameRunner(engine, dm=FakeDM(), character=FakeCharacterAgent())

        success, hint = runner.execute_dm_reaction({"character_id": "hero", "tool": "speak", "result": {"status": "success"}})
        self.assertTrue(success)
        self.assertEqual(hint, "hero")
        self.assertTrue(any(call[0] == "narrate" for call in engine.calls))

    def test_execute_character_turn_uses_soft_hint(self):
        engine = FakeEngine()
        character = FakeCharacterAgent()
        runner = GameRunner(engine, dm=FakeDM(), character=character)

        result = runner.execute_character_turn(dm_prompt="hero")
        self.assertTrue(result["success"])
        self.assertEqual(character.last_prompt, "hero")
        self.assertTrue(any(call[0] == "speak" for call in engine.calls))

    def test_finalize_session_writes_review(self):
        engine = FakeEngine()
        reviewer = FakeReviewer()

        session_dir = tempfile.mkdtemp(prefix="test_session_")
        llm_log_path = os.path.join(session_dir, "llm_log.jsonl")
        runner = GameRunner(
            engine,
            dm=FakeDM(),
            character=FakeCharacterAgent(),
            reviewer=reviewer,
            session_dir=session_dir,
            llm_log_path=llm_log_path,
            report_generator=lambda *_: False,
        )

        runner.finalize_session()
        review_path = os.path.join(session_dir, "review.json")
        self.assertTrue(os.path.exists(review_path))
        with open(review_path, "r", encoding="utf-8") as f:
            d = json.load(f)
            self.assertIn("summary", d)


if __name__ == "__main__":
    unittest.main()

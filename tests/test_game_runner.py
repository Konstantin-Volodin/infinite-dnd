import os
import json
import tempfile
import unittest
from types import SimpleNamespace

from run_game import GameRunner, output, OutputLevel, _default_runner


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.state = SimpleNamespace(characters={}, history=[], time=0, story_beats=[])

    def execute_tool(self, tool, **kwargs):
        self.calls.append((tool, kwargs))
        return {"status": "success"}

    def save_state(self):
        pass

    def advance_time(self):
        pass


class FakeDM:
    def __init__(self):
        self.decide_calls = []

    def decide_action(self, state, guidance=""):
        self.decide_calls.append(guidance)
        return {"tool": "say", "arguments": {"message": "ok"}}

    def generate_new_item(self, state, item, loc):
        return {"tool": "create", "item_name": item, "location_id": loc}

    def generate_new_location(self, state, target, origin):
        return {"tool": "create_location", "target_name": target, "origin_id": origin}


class FakeReviewer:
    def summarize_session(self, state):
        return {"summary": "ok"}


class GameRunnerTests(unittest.TestCase):
    def test_execute_dm_action_calls_engine(self):
        engine = FakeEngine()
        dm = FakeDM()
        runner = GameRunner(engine, dm)

        result = runner.execute_dm_action(guidance="say hi")
        self.assertTrue(result)
        self.assertTrue(any(call[0] == "say" for call in engine.calls))

    def test_execute_character_action_item_missing_and_intent(self):
        engine = FakeEngine()

        # character
        char = SimpleNamespace(name="Hero", location="loc1")
        engine.state.characters["hero"] = char

        # engine behavior: use_item fails with item_missing first, then create succeeds and retry succeeds
        call_count = {"use_item": 0}

        def execute_tool(tool, **kwargs):
            if tool == "use_item":
                call_count["use_item"] += 1
                if call_count["use_item"] == 1:
                    return {"status": "failed", "code": "item_missing", "item_name": "gem"}
                else:
                    return {"status": "success", "intent": "I use the gem"}
            elif tool == "create":
                return {"status": "success"}
            else:
                return {"status": "success"}

        engine.execute_tool = execute_tool

        dm = FakeDM()
        runner = GameRunner(engine, dm)

        success = runner.execute_character_action("hero", guidance="use the item")
        self.assertTrue(success)

    def test_finalize_session_writes_review(self):
        engine = FakeEngine()
        dm = FakeDM()
        reviewer = FakeReviewer()

        session_dir = tempfile.mkdtemp(prefix="test_session_")
        llm_log_path = os.path.join(session_dir, "llm_log.jsonl")
        runner = GameRunner(engine, dm, reviewer=reviewer, session_dir=session_dir, llm_log_path=llm_log_path)

        runner.finalize_session()
        review_path = os.path.join(session_dir, "review.json")
        self.assertTrue(os.path.exists(review_path))
        with open(review_path, "r", encoding="utf-8") as f:
            d = json.load(f)
            self.assertIn("summary", d)


if __name__ == "__main__":
    unittest.main()

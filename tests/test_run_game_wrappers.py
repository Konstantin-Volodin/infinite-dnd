import io
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

import run_game as rg


class DummyRunner:
    def __init__(self):
        self.messages = []

    def output(self, msg, level=None):
        self.messages.append(msg)


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
    def decide_action(self, state, guidance=""):
        return {"tool": "say", "arguments": {"message": "ok"}}


class FakeStoryteller:
    def plan_scene(self, state):
        return {"scene_type": "dm_scene", "dm_guidance": "go"}


class FakeDirector:
    def decide_next_actors(self, state):
        return [{"actor": "dm", "guidance": ""}]


class RunGameWrappersTests(unittest.TestCase):
    def test_output_delegate_and_fallback(self):
        # Fallback (no default runner)
        old = rg._default_runner
        rg._default_runner = None

        rg.output_level = rg.OutputLevel.VERBOSE
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            rg.output("hello", rg.OutputLevel.DEFAULT)
            self.assertIn("hello", buf.getvalue())
        finally:
            sys.stdout = old_stdout

        # Delegate to a dummy runner
        dummy = DummyRunner()
        rg._default_runner = dummy
        rg.output("bye", rg.OutputLevel.DEFAULT)
        self.assertIn("bye", dummy.messages)

        # restore
        rg._default_runner = old

    def test_run_scene_loop_wrapper_executes(self):
        engine = FakeEngine()
        dm = FakeDM()
        storyteller = FakeStoryteller()
        session_dir = tempfile.mkdtemp(prefix="test_session_")
        llm_log_path = os.path.join(session_dir, "llm_log.jsonl")

        rg.run_scene_loop(engine, dm, storyteller, max_scenes=1, session_dir=session_dir, llm_log_path=llm_log_path)
        self.assertTrue(any(call[0] == "say" for call in engine.calls))

    def test_run_game_loop_wrapper_executes(self):
        engine = FakeEngine()
        dm = FakeDM()
        director = FakeDirector()
        session_dir = tempfile.mkdtemp(prefix="test_session_")
        llm_log_path = os.path.join(session_dir, "llm_log.jsonl")

        rg.run_game_loop(engine, dm, director, max_actions=1, session_dir=session_dir, llm_log_path=llm_log_path)
        self.assertTrue(any(call[0] == "say" for call in engine.calls))


if __name__ == "__main__":
    unittest.main()

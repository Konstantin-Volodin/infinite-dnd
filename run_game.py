"""Infinite D&D - ping-pong loop: Character acts, DM reacts."""
from __future__ import annotations

import os
import time
from datetime import datetime
from src.config import Config
from src.engine import Engine
from src.agents import DMAgent, CharacterAgent
from src.core.llm import setup_logger
from src.core.utils import slugify


# ANSI Colors
class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


# Output verbosity
class OutputLevel:
    QUIET = 0
    DEFAULT = 1
    VERBOSE = 2


output_level = OutputLevel.DEFAULT


class GameRunner:
    """Encapsulates a single game/session run: loops, logging, and finalization."""

    def __init__(
        self,
        engine,
        *,
        session_dir = None,
        llm_log_path = None,
        dm: DMAgent | None = None,
        character: CharacterAgent | None = None,
        output_level: int = OutputLevel.DEFAULT,
    ):
        """Initialize the GameRunner with agents and settings."""
        self.engine = engine

        self.dm = dm or DMAgent()
        self.character = character or CharacterAgent()

        self.session_dir = session_dir
        self.llm_log_path = llm_log_path
        self.output_level = output_level

    def output(self, msg: str, level: int = OutputLevel.DEFAULT):
        """Instance-scoped output respecting this runner's verbosity."""
        if self.output_level >= level:
            print(msg)

    def _canonical_character_id(self, raw_id: str | None) -> str | None:
        """Map loosely formatted character ids (e.g., different casing) to known ids."""
        if not raw_id or not isinstance(raw_id, str):
            return raw_id
        if raw_id in self.engine.state.characters:
            return raw_id

        lowered = raw_id.lower()
        slugged = slugify(raw_id)
        for cid in self.engine.state.characters.keys():
            if cid.lower() == lowered or slugify(cid) == slugged:
                return cid
        return raw_id

    def _expand_tool_calls(self, action: dict, default_character_id: str | None = None) -> list[dict]:
        calls = []
        if "all_calls" in action:
            for call in action["all_calls"]:
                payload = call.get("arguments", {}).copy()
                payload["tool"] = call.get("tool")
                if default_character_id and "character_id" not in payload:
                    payload["character_id"] = default_character_id
                if "character_id" in payload:
                    payload["character_id"] = self._canonical_character_id(payload.get("character_id"))
                calls.append(payload)
        else:
            payload = action.copy()
            if default_character_id and "character_id" not in payload:
                payload["character_id"] = default_character_id
            if "character_id" in payload:
                payload["character_id"] = self._canonical_character_id(payload.get("character_id"))
            calls.append(payload)
        return calls

    def execute_character_turn(self, dm_prompt: str | None = None) -> dict:
        """Execute one character turn and return compact action summary."""
        action = self.character.decide_and_act(self.engine.state, dm_prompt=dm_prompt)
        character_id = self._canonical_character_id(action.get("character_id"))
        action["character_id"] = character_id
        calls = self._expand_tool_calls(action, default_character_id=character_id)

        any_success = False
        last_result = None

        for call in calls:
            tool = call.get("tool")
            if not tool:
                continue

            payload = {k: v for k, v in call.items() if k != "tool"}
            result = self.engine.execute_tool(tool, **payload)

            if result.get("code") == "location_missing":
                target = result.get("target_name")
                origin = result.get("origin_id")
                self.output(f"  ✨ Creating '{target}'...", OutputLevel.VERBOSE)
                gen = self.dm.generate_new_location(self.engine.state, target, origin)
                self.engine.execute_tool(gen.get("tool"), **{k: v for k, v in gen.items() if k != "tool"})
                result = self.engine.execute_tool(tool, **payload)

            if result.get("code") == "item_missing":
                item = result.get("item_name")
                char = self.engine.state.characters.get(call.get("character_id", ""))
                loc = char.location if char else ""
                self.output(f"  ✨ Checking '{item}'...", OutputLevel.VERBOSE)
                gen = self.dm.generate_new_item(self.engine.state, item, loc)
                if gen.get("tool") == "create":
                    self.engine.execute_tool(gen.get("tool"), **{k: v for k, v in gen.items() if k != "tool"})
                    result = self.engine.execute_tool(tool, **payload)

            if result.get("status") == "success":
                any_success = True

            last_result = result

        return {
            "character_id": character_id,
            "tool": action.get("tool"),
            "result": last_result or {"status": "error", "message": "No character action executed"},
            "success": any_success,
        }

    def execute_dm_reaction(self, last_action: dict | None) -> tuple[bool, str | None]:
        """Execute one DM reactive turn and return success + soft hint."""
        # Resolve the location of the last-acting character for narration tagging
        narrate_location = ""
        if last_action:
            char_id = last_action.get("character_id", "")
            char = self.engine.state.characters.get(char_id)
            if char:
                narrate_location = char.location

        action = self.dm.react(self.engine.state, last_action=last_action)
        calls = self._expand_tool_calls(action)

        any_success = False
        prompted_character = None

        for call in calls:
            tool = call.get("tool")
            if not tool:
                continue

            payload = {k: v for k, v in call.items() if k != "tool"}
            if tool == "narrate":
                payload["location"] = narrate_location
            result = self.engine.execute_tool(tool, **payload)
            if result.get("status") == "success":
                any_success = True

            if tool == "narrate":
                hint = call.get("prompts_character")
                hint = self._canonical_character_id(hint)
                if isinstance(hint, str) and hint in self.engine.state.characters:
                    prompted_character = hint

        return any_success, prompted_character

    def run_pingpong_loop(self, max_turns: int = 30):
        """Character acts -> DM reacts -> repeat."""
        self.output(f"\n{Colors.CYAN}{'=' * 50}")
        self.output("  GAME START (PING-PONG)")
        self.output(f"{'=' * 50}{Colors.ENDC}")

        pending_character_hint = None
        turns = 0

        while turns < max_turns:
            turns += 1

            if self.output_level == OutputLevel.QUIET:
                self.output(f"Turn {turns}: Character -> DM")
            else:
                self.output(f"\n{Colors.CYAN}--- Turn {turns} ---{Colors.ENDC}")
                if pending_character_hint:
                    self.output(f"{Colors.GREEN}{Colors.BOLD}Character (hint: {pending_character_hint}){Colors.ENDC}")
                else:
                    self.output(f"{Colors.GREEN}{Colors.BOLD}Character{Colors.ENDC}")

            last_action = self.execute_character_turn(dm_prompt=pending_character_hint)
            pending_character_hint = None

            if not last_action.get("success"):
                self.output(f"  {Colors.RED}(Character turn had no effect){Colors.ENDC}", OutputLevel.VERBOSE)

            if self.output_level != OutputLevel.QUIET:
                self.output(f"{Colors.YELLOW}{Colors.BOLD}Dungeon Master{Colors.ENDC}")

            dm_success, next_hint = self.execute_dm_reaction(last_action)
            if not dm_success:
                self.output(f"  {Colors.RED}(DM reaction had no effect){Colors.ENDC}", OutputLevel.VERBOSE)

            pending_character_hint = next_hint

            if turns % 3 == 0:
                self.engine.advance_time()

            time.sleep(0.2)

        self.output(f"\n{Colors.CYAN}{'=' * 50}")
        self.output(f"  SESSION COMPLETE - {turns} turns")
        self.output(f"{'=' * 50}{Colors.ENDC}")

    def run(self, *, turns: int = 30):
        self.run_pingpong_loop(max_turns=turns)


def main():
    global output_level

    print(f"\n{Colors.CYAN}{Colors.BOLD}=== Infinite D&D ==={Colors.ENDC}")

    # setup logs
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = os.path.join(Config.PATHS["logs_dir"], f"session-{timestamp}")
    os.makedirs(log_dir, exist_ok=True)
    llm_log_path = os.path.join(log_dir, "llm_log.jsonl")
    print(f"📂 Logs: {log_dir}")
    setup_logger(llm_log_path)

    # handle reset
    state_file = Config.PATHS["state_file"]
    if Config.RESET_WORLD and os.path.exists(state_file):
        os.remove(state_file)
        print("🔄 World state reset!")

    # initialize engine
    try:
        engine = Engine()
    except Exception as e:
        print(f"⚠️ Failed to initialize: {e}")
        return

    # check for existing history
    history_count = len(engine.state.history)
    if history_count > 0:
        print(f"📜 Continuing from turn {engine.state.time} ({history_count} events)")

    runner = GameRunner(
        engine,
        dm=DMAgent(),
        character=CharacterAgent(),
        session_dir=log_dir,
        llm_log_path=llm_log_path,
        output_level=output_level,
    )

    print("🎭 Mode: Ping-pong (Character ↔ DM)")
    runner.run(turns=Config.MAX_SCENES)


if __name__ == "__main__":
    main()

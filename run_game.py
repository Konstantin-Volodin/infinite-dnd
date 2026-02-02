"""
Infinite D&D - AI-driven roleplaying game.

Scene-based game loop: Storyteller plans scenes, DM writes prose, 
Characters make decisions at key moments.
"""

import os
import time
from datetime import datetime
from src.config import Config
from src.engine import Engine
from src.agents import DMAgent, CharacterAgent, DirectorAgent, ReviewerAgent, StorytellerAgent
from src.core.llm import setup_logger
from src.core.log_viewer import generate_log_report


# ANSI Colors
class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


# Output verbosity
class OutputLevel:
    QUIET = 0
    DEFAULT = 1
    VERBOSE = 2


output_level = OutputLevel.DEFAULT

# Default runner for compatibility with modules that import run_game.output directly.
_default_runner = None


def _fallback_output(msg: str, level: int = OutputLevel.DEFAULT):
    """Original behavior for printing when no runner is present."""
    if output_level >= level:
        print(msg)


def output(msg: str, level: int = OutputLevel.DEFAULT):
    """Module-level output that delegates to a GameRunner if available.

    This keeps backward compatibility for modules that import `run_game.output`.
    """
    if _default_runner is not None:
        _default_runner.output(msg, level=level)
    else:
        _fallback_output(msg, level=level)


class GameRunner:
    """Encapsulates a single game/session run: loops, logging, and finalization."""

    def __init__(
        self,
        engine,
        *,
        session_dir = None,
        llm_log_path = None,
        output_level:int = OutputLevel.DEFAULT,
        report_generator=None,
    ):
        """Initialize the GameRunner with agents and settings."""
        self.engine = engine

        # LLM agents
        self.dm = DMAgent() 
        self.director = DirectorAgent()
        self.storyteller = StorytellerAgent()
        self.reviewer = ReviewerAgent()

        self.session_dir = session_dir
        self.llm_log_path = llm_log_path
        self.output_level = output_level
        self.report_generator = report_generator or generate_log_report

    def output(self, msg: str, level: int = OutputLevel.DEFAULT):
        """Instance-scoped output respecting this runner's verbosity."""
        if self.output_level >= level:
            print(msg)

    def execute_dm_action(self, guidance: str = "") -> bool:
        """Execute DM action(s). Returns True if any succeeded."""
        action = self.dm.decide_action(self.engine.state, guidance=guidance)

        calls = action.get("all_calls", [{"tool": action.get("tool"), "arguments": action}])
        any_success = False

        for call in calls:
            tool = call.get("tool") or call.get("arguments", {}).get("tool")
            args = call.get("arguments", call)
            result = self.engine.execute_tool(tool, **args)
            if result.get("status") == "success":
                any_success = True

        return any_success

    def execute_character_action(self, char_id: str, guidance: str = "") -> bool:
        """Execute character action(s). Returns True if any succeeded."""
        char = self.engine.state.characters.get(char_id)
        if not char:
            self.output(f"  ⚠️ Unknown character: {char_id}", OutputLevel.VERBOSE)
            return False

        agent = CharacterAgent(char_id)
        action = agent.decide_action(self.engine.state, guidance=guidance)

        # Collect all tool calls
        calls = []
        if "all_calls" in action:
            for call in action["all_calls"]:
                cmd = call.get("arguments", {}).copy()
                cmd["tool"] = call.get("tool")
                cmd["character_id"] = char_id
                calls.append(cmd)
        else:
            action["character_id"] = char_id
            calls.append(action)

        any_success = False
        for action in calls:
            result = self.engine.execute_tool(action["tool"], **action)

            if result.get("status") == "success":
                any_success = True

            # Handle DM narration for character actions (speak, act)
            if result.get("intent"):
                dm_guidance = result.get("dm_guidance", "Narrate what happens.")
                intent = result.get("intent", "")
                # Pass the character's intent to the DM for prose narration
                self.execute_dm_action(guidance=f"{dm_guidance}\n\nCharacter intent: {intent}")

            # Handle dynamic location generation
            if result.get("code") == "location_missing":
                target = result.get("target_name")
                origin = result.get("origin_id")
                self.output(f"  ✨ Creating '{target}'...", OutputLevel.VERBOSE)

                gen = self.dm.generate_new_location(self.engine.state, target, origin)
                self.engine.execute_tool(gen["tool"], **gen)
                # Retry the move
                self.engine.execute_tool(action["tool"], **action)

            # Handle dynamic item generation
            if result.get("code") == "item_missing":
                item = result.get("item_name")
                loc = char.location_id
                self.output(f"  ✨ Checking '{item}'...", OutputLevel.VERBOSE)

                gen = self.dm.generate_new_item(self.engine.state, item, loc)
                if gen["tool"] == "create":
                    self.engine.execute_tool(gen["tool"], **gen)
                    self.engine.execute_tool(action["tool"], **action)

        return any_success

    def execute_decision_point(self, char_id: str, question: str, stakes: str) -> str:
        """Have a character make a decision at a key story moment.
        Returns a description of what they decided.
        """
        char = self.engine.state.characters.get(char_id)
        if not char:
            return f"Unknown character: {char_id}"

        agent = CharacterAgent(char_id)
        # Frame the decision as guidance
        guidance = f"""
CRITICAL DECISION POINT:
{question}

Stakes: {stakes}

Make your choice. Don't deliberate - DECIDE and ACT.
""".strip()

        action = agent.decide_action(self.engine.state, guidance=guidance)

        # Execute the character's chosen action
        calls = []
        if "all_calls" in action:
            for call in action["all_calls"]:
                cmd = call.get("arguments", {}).copy()
                cmd["tool"] = call.get("tool")
                cmd["character_id"] = char_id
                calls.append(cmd)
        else:
            action["character_id"] = char_id
            calls.append(action)

        decision_summary = []
        for act in calls:
            result = self.engine.execute_tool(act["tool"], **act)
            if result.get("intent"):
                decision_summary.append(result.get("intent"))
            elif result.get("message"):
                decision_summary.append(result.get("message"))

        return " ".join(decision_summary) if decision_summary else "The character hesitated."

    def run_scene_loop(self, max_scenes: int = 15):
        """Scene-based game loop."""
        self.output(f"\n{Colors.CYAN}{'=' * 50}")
        self.output("  STORY BEGINS")
        self.output(f"{'=' * 50}{Colors.ENDC}")

        scenes_played = 0

        while scenes_played < max_scenes:
            scenes_played += 1

            try:
                # Storyteller plans the next beat
                self.output(f"\n{Colors.BLUE}--- Scene {scenes_played} ---{Colors.ENDC}")

                scene_plan = self.storyteller.plan_scene(self.engine.state)
                scene_type = scene_plan.get("scene_type", "dm_scene")

                if scene_type == "dm_scene":
                    dm_guidance = scene_plan.get("dm_guidance", "Continue the story.")
                    purpose = scene_plan.get("dramatic_purpose", "advancement")
                    beat_id = scene_plan.get("beat_id", "")

                    self.output(f"  {Colors.YELLOW}[{purpose.upper()}]{Colors.ENDC}", OutputLevel.VERBOSE)

                    self.execute_dm_action(guidance=dm_guidance)

                    if beat_id and beat_id not in self.engine.state.story_beats:
                        self.engine.state.story_beats.append(beat_id)
                        self.engine.save_state()

                elif scene_type == "decision_point":
                    char_id = scene_plan.get("decision_for", "")
                    question = scene_plan.get("decision_question", "What do you do?")
                    stakes = scene_plan.get("stakes", "")
                    setup = scene_plan.get("dm_guidance", "")

                    char = self.engine.state.characters.get(char_id)
                    char_name = char.name if char else char_id

                    self.output(f"  {Colors.GREEN}[DECISION: {char_name}]{Colors.ENDC}")
                    self.output(f"  {Colors.CYAN}\"{question}\"{Colors.ENDC}", OutputLevel.VERBOSE)

                    if setup:
                        self.execute_dm_action(guidance=setup)

                    decision = self.execute_decision_point(char_id, question, stakes)

                    outcome_guidance = f"Narrate the outcome: {char_name} decided: {decision}"
                    self.execute_dm_action(guidance=outcome_guidance)

                elif scene_type == "transition":
                    narration = scene_plan.get("dm_guidance", scene_plan.get("narration", ""))
                    to_loc = scene_plan.get("to_location", "")
                    chars = scene_plan.get("characters", [])

                    self.output(f"  {Colors.BLUE}[TRANSITION]{Colors.ENDC}", OutputLevel.VERBOSE)

                    for char_id in chars:
                        if to_loc:
                            self.engine.execute_tool("move", character_id=char_id, location_id=to_loc)

                    if narration:
                        self.execute_dm_action(guidance=narration)

                # Generate live logs
                if self.llm_log_path and self.session_dir:
                    self.report_generator(self.llm_log_path, self.session_dir)

                # Advance time periodically
                if scenes_played % 3 == 0:
                    self.engine.advance_time()

                time.sleep(0.3)
            
            except Exception as e:
                import traceback
                self.output(f"\n{Colors.RED}CRASH IN SCENE LOOP:{Colors.ENDC} {e}")
                self.output(traceback.format_exc())
                break

        self.output(f"\n{Colors.CYAN}{'=' * 50}")
        self.output(f"  STORY PAUSED - {scenes_played} scenes")
        self.output(f"{'=' * 50}{Colors.ENDC}")

    def run_game_loop(self, max_actions: int = 30):
        """Classic Director game loop."""
        self.output(f"\n{Colors.CYAN}{'=' * 50}")
        self.output("  GAME START")
        self.output(f"{'=' * 50}{Colors.ENDC}")

        actions_taken = 0

        while actions_taken < max_actions:
            sequence = self.director.decide_next_actors(self.engine.state)
            if not sequence:
                sequence = [{"actor": "dm", "guidance": "Advance the story."}]

            for turn in sequence:
                if actions_taken >= max_actions:
                    break

                actions_taken += 1
                actor_id = turn.get("actor", "dm")
                guidance = turn.get("guidance", "")

                if actor_id == "dm":
                    name = "Dungeon Master"
                    color = Colors.YELLOW
                else:
                    char = self.engine.state.characters.get(actor_id)
                    name = char.id if char else actor_id
                    color = Colors.GREEN

                if self.output_level == OutputLevel.QUIET:
                    self.output(f"Turn {actions_taken}: {name}")
                else:
                    self.output(f"\n{Colors.CYAN}--- Turn {actions_taken} ---{Colors.ENDC}")
                    self.output(f"{color}{Colors.BOLD}{name}{Colors.ENDC}")

                if actor_id == "dm":
                    success = self.execute_dm_action(guidance)
                else:
                    success = self.execute_character_action(actor_id, guidance)

                if not success:
                    self.output(f"  {Colors.RED}(No effect){Colors.ENDC}", OutputLevel.VERBOSE)

                if self.llm_log_path and self.session_dir:
                    self.report_generator(self.llm_log_path, self.session_dir)

                if actions_taken % 5 == 0:
                    self.engine.advance_time()

                time.sleep(0.2)

        self.output(f"\n{Colors.CYAN}{'=' * 50}")
        self.output(f"  SESSION COMPLETE - {actions_taken} actions")
        self.output(f"{'=' * 50}{Colors.ENDC}")

    def finalize_session(self):
        """Generate reports and run reviewer summary (if present)."""
        if getattr(self, "_finalized", False):
            return
            
        self.output("\n📊 Generating session reports...")

        if self.report_generator and self.report_generator(self.llm_log_path, self.session_dir):
            self.output("   📖 story.html")
            self.output("   📝 story.md")
            self.output("   🔧 debug_viewer.html")

        try:
            if self.reviewer:
                self.output("\n📝 Generating session review...")
                review = self.reviewer.summarize_session(self.engine.state)
                review_path = os.path.join(self.session_dir, "review.json")
                with open(review_path, "w", encoding="utf-8") as f:
                    import json

                    f.write(json.dumps(review, indent=2, ensure_ascii=False))
                self.output(f"   Saved to: {review_path}")
        except Exception as e:
            self.output(f"   Could not generate review: {e}")

        # mark finalized so callers can safely check
        self._finalized = True

    def run(self, mode: str = "scene", *, scenes: int = 15):
        """Convenience method to run the session and finalize in a finally block."""
        # Ensure logger is set up
        # setup_logger already called in main


        try:
            if mode == "classic":
                self.run_game_loop(max_actions=scenes * 2)
            else:
                self.run_scene_loop(max_scenes=scenes)
        finally:
            self.finalize_session()


def execute_dm_action(engine: Engine, dm: DMAgent, guidance: str = "") -> bool:
    """Execute DM action(s). Returns True if any succeeded."""
    # Backwards-compatible wrapper that delegates to GameRunner
    runner = GameRunner(engine, dm)
    return runner.execute_dm_action(guidance=guidance)


def execute_character_action(
    engine: Engine, dm: DMAgent, char_id: str, guidance: str = ""
) -> bool:
    """Execute character action(s). Returns True if any succeeded."""
    runner = GameRunner(engine, dm)
    return runner.execute_character_action(char_id, guidance=guidance)


def execute_decision_point(
    engine: Engine, dm: DMAgent, char_id: str, question: str, stakes: str
) -> str:
    """
    Have a character make a decision at a key story moment.
    Returns a description of what they decided.
    """
    runner = GameRunner(engine, dm)
    return runner.execute_decision_point(char_id, question, stakes)


def run_scene_loop(
    engine: Engine,
    dm: DMAgent,
    storyteller: StorytellerAgent,
    max_scenes: int = 15,
    session_dir: str = None,
    llm_log_path: str = None,
):
    """
    Scene-based game loop:
    1. Storyteller plans a scene beat
    2. DM writes the scene OR character makes a decision
    3. Repeat
    """
    runner = GameRunner(
        engine, 
        dm, 
        storyteller=storyteller, 
        session_dir=session_dir, 
        llm_log_path=llm_log_path
    )
    return runner.run_scene_loop(max_scenes=max_scenes)


def run_game_loop(
    engine: Engine,
    dm: DMAgent,
    director: DirectorAgent,
    max_actions: int = 30,
    session_dir: str = None,
    llm_log_path: str = None,
):
    """Main game loop: Director picks actors, actors act, repeat."""
    runner = GameRunner(
        engine, 
        dm, 
        director=director, 
        session_dir=session_dir,
        llm_log_path=llm_log_path,
    )
    return runner.run_game_loop(max_actions=max_actions)


def finalize_session(
    session_dir: str, llm_log_path: str, engine: Engine, reviewer: ReviewerAgent
):
    runner = GameRunner(
        engine, 
        DMAgent(), 
        reviewer=reviewer, 
        session_dir=session_dir, 
        llm_log_path=llm_log_path
    )
    return runner.finalize_session()


def main():
    global output_level
    global _default_runner

    output(f"\n{Colors.CYAN}{Colors.BOLD}=== Infinite D&D ==={Colors.ENDC}")
    
    # setup logs
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = os.path.join(Config.PATHS["logs_dir"], f"session-{timestamp}")
    os.makedirs(log_dir, exist_ok=True)
    llm_log_path = os.path.join(log_dir, "llm_log.jsonl")
    output(f"📂 Logs: {log_dir}")
    setup_logger(llm_log_path)

    # handle reset
    state_file = Config.PATHS["state_file"]
    if Config.RESET_WORLD and os.path.exists(state_file):
        os.remove(state_file)
        output("🔄 World state reset!")
    
    # initialize engine
    try:
        engine = Engine()
    except Exception as e:
        output(f"⚠️ Failed to initialize: {e}")
        return

    # check for existing history
    history_count = len(engine.state.history)
    if history_count > 0:
        output(f"📜 Continuing from turn {engine.state.time} ({history_count} events)")

    runner = None
    try:
        if Config.GAME_MODE == "classic":
            output(f"🎭 Mode: Classic (Director)")
            runner = GameRunner(
                engine,
                session_dir=log_dir,
                llm_log_path=llm_log_path,
                output_level=output_level,
            )
            # Set module-level default runner for compatibility
            _default_runner = runner

            runner.run(mode="classic", scenes=Config.MAX_SCENES)
        else:
            storyteller = StorytellerAgent()
            output(f"📖 Mode: Scene-based (Storyteller)")
            runner = GameRunner(
                engine,
                session_dir=log_dir,
                llm_log_path=llm_log_path,
                output_level=output_level,
            )
            # Set module-level default runner for compatibility
            _default_runner = runner

            runner.run(mode="scene", scenes=Config.MAX_SCENES)
    finally:
        
        # Ensure session is finalized if something went wrong before runner.run completed
        if runner is not None:
            try:
                runner.finalize_session()
            except Exception:
                pass


if __name__ == "__main__":
    main()

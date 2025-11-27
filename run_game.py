import os
import time
import argparse
from datetime import datetime
from src.engine import Engine
from src.agents import DMAgent, CharacterAgent, DirectorAgent, ReviewerAgent
from src.core.llm import setup_logger
from src.core.log_viewer import generate_log_report

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def run_action(engine: Engine, dm: DMAgent, actor_id: str, guidance: str = "") -> tuple[bool, str]:
    """Execute an action for the given actor. Returns (success, failure_message).
    
    Args:
        guidance: Optional suggestion from director about what action to take.
    """
    # Track by checking the last history item before/after
    history_before = engine.state.history[-1] if engine.state.history else None
    
    result = None
    
    if actor_id == "dm":
        # DM now returns structured JSON response
        action = dm.decide_action(engine.state, guidance=guidance)
        result = engine.execute_tool(action["tool"], **action)
    else:
        # It's a character
        char = engine.state.characters.get(actor_id)
        if not char:
            print(f"  ⚠️ Unknown actor: {actor_id}")
            return False, "Unknown actor"
        
        char_agent = CharacterAgent(actor_id)
        root_action = char_agent.decide_action(engine.state, guidance=guidance)

        # Prepare list of actions to execute
        actions_to_run = []
        if "all_calls" in root_action:
            for call in root_action["all_calls"]:
                cmd = call["arguments"].copy()
                cmd["tool"] = call["tool"]
                cmd["character_id"] = actor_id
                actions_to_run.append(cmd)
        else:
            # Fallback
            if "character_id" not in root_action:
                root_action["character_id"] = actor_id
            actions_to_run.append(root_action)

        # Execute all actions in sequence
        for action in actions_to_run:
            result = engine.execute_tool(action["tool"], **action)
            
            # Check for errors and return them
            if result.get("status") == "error":
                failure_msg = result.get("message", "Action failed")
                print(f"  ⚠️ Action failed: {failure_msg}")
                return False, failure_msg
            
            # Handle examine action - DM should describe what they find
            if result.get("requires_dm_response"):
                examine_target = result.get("examine_target", "something")
                location_id = result.get("location_id", "")
                print(f"  🔍 DM responding to examination...")
                
                dm_guidance = f"DESCRIBE what the character finds when examining '{examine_target}'. Reveal a clue, danger, or interesting detail. Location: {location_id}"
                dm_action = dm.decide_action(engine.state, guidance=dm_guidance)
                engine.execute_tool(dm_action["tool"], **dm_action)
            
            # Check for dynamic location generation trigger
            if result.get("code") == "location_missing":
                target_name = result.get("target_name")
                origin_id = result.get("origin_id")
                print(f"  ✨ Dynamic Generation Triggered: Creating '{target_name}'...")
                
                gen_action = dm.generate_new_location(engine.state, target_name, origin_id)
                gen_result = engine.execute_tool(gen_action["tool"], **gen_action)
                
                if gen_result.get("status") == "success":
                    print(f"  🔄 Retrying move to '{target_name}'...")
                    result = engine.execute_tool(action["tool"], **action)
            
            # Check for dynamic item generation trigger
            if result.get("code") == "item_missing":
                item_name = result.get("item_name")
                char_id = result.get("character_id")
                char = engine.state.characters.get(char_id)
                loc_id = char.location_id
                
                print(f"  ✨ Dynamic Item Check: Validating '{item_name}'...")
                
                gen_action = dm.generate_new_item(engine.state, item_name, loc_id)
                gen_result = engine.execute_tool(gen_action["tool"], **gen_action)
                
                if gen_result.get("status") == "success" and gen_action["tool"] == "create_item":
                    print(f"  🔄 Retrying pickup of '{item_name}'...")
                    result = engine.execute_tool(action["tool"], **action)

            # Handle skill_required responses by performing skill check
            if result.get("code") == "skill_required":
                skill = result.get("skill")
                difficulty = result.get("difficulty")
                location_id = result.get("location_id") or (char.location_id if char else None)
                print(f"  🎲 Skill check required: {skill} (DC {difficulty})")
                skill_res = engine.execute_tool("attempt_skill", character_id=actor_id, skill=skill, action_description=result.get("action_description", ""), difficulty=difficulty)
                # If check result is success, ask DM to narrate; otherwise, trigger failure and increase tension
                if skill_res.get("success"):
                    print("  ✅ Skill check SUCCESS")
                    dm_guidance = f"DESCRIBE the success: The character succeeded a {skill} check and discovers something useful at {location_id}. Reveal a clue or path."
                    dm_action = dm.decide_action(engine.state, guidance=dm_guidance)
                    engine.execute_tool(dm_action["tool"], **dm_action)
                else:
                    print("  ❌ Skill check FAILED")
                    # Increase narrative tension and ask DM to narrate a failure (maybe a trap)
                    engine.state.narrative.tension = "high"
                    engine.save_state()
                    dm_guidance = f"DESCRIBE the failure: The character fails the {skill} check and something goes wrong at {location_id}. Add tension and consequences."
                    dm_action = dm.decide_action(engine.state, guidance=dm_guidance)
                    engine.execute_tool(dm_action["tool"], **dm_action)
                # after handling skill, continue to next actor
                continue
            
            # Handle invalid target responses to provide helpful feedback
            if result.get("code") == "invalid_target":
                msg = result.get("message", "Invalid target")
                allowed = result.get("allowed_targets") or result.get("present_features") or result.get("allowed_items")
                print(f"  ⚠️ Invalid target: {msg}")
                if allowed:
                    print(f"    Allowed: {allowed}")
                # Try one automatic retry by re-asking the character with suggestions
                if actor_id != "dm":
                    print("  🔁 Re-requesting action with guidance to choose an allowed target...")
                    guidance_extra = ''
                    if isinstance(allowed, list):
                        guidance_extra = f"\nAllowed targets: {', '.join(allowed)}"
                    char_agent = CharacterAgent(actor_id)
                    retry_action = char_agent.decide_action(engine.state, guidance=guidance + guidance_extra)
                    # Attach character id
                    if "character_id" not in retry_action:
                        retry_action["character_id"] = actor_id
                    retry_result = engine.execute_tool(retry_action["tool"], **retry_action)
                    if retry_result.get("status") == "success":
                        result = retry_result
                        # continue handling any skill checks or DM responses
                    else:
                        # Give up and report failure
                        failure_msg = retry_result.get("message", "Invalid target after retry")
                        print(f"  ⚠️ Retry failed: {failure_msg}")
                        return False, failure_msg
                else:
                    return False, msg
    
    # Check if a new event was added (last item changed)
    history_after = engine.state.history[-1] if engine.state.history else None
    success = history_before != history_after
    return success, "" if success else "No action effect"


def detect_stuck_state(history: list) -> tuple[bool, str]:
    """Detect if the story is stuck in a loop. Returns (is_stuck, reason)."""
    if len(history) < 6:
        return False, ""
    
    recent = history[-8:]
    
    # Count movement actions
    move_count = sum(1 for e in recent if "moved to" in e.lower())
    if move_count >= 5:
        return True, "excessive_movement"
    
    # Detect repeated questions/topics
    recent_text = " ".join(recent).lower()
    repeated_phrases = ["my brother", "anyone near", "did you see", "what do you know"]
    for phrase in repeated_phrases:
        if recent_text.count(phrase) >= 3:
            return True, "repetitive_dialogue"
    
    # Detect no DM activity for too long
    dm_count = sum(1 for e in recent if e.lower().startswith("dm:"))
    if dm_count == 0 and len(recent) >= 6:
        return True, "no_dm_events"
    
    # Detect exact repetition of the last event
    if len(history) >= 2 and history[-1] == history[-2]:
        return True, "exact_repetition"
    
    return False, ""


def update_stall_counter(engine: Engine, actor_id: str, action_taken: bool):
    """Update the stall counter based on what just happened.
    
    Resets on meaningful progress, increments otherwise.
    """
    history = engine.state.history
    if not history:
        return
    
    last_event = history[-1].lower()
    
    # Events that indicate meaningful progress (reset stall counter)
    progress_indicators = [
        "dm:",           # DM narrated something
        "attacked",      # Combat happened
        "defeated",      # Combat resolved
        "picked up",     # Item acquired
        "moved to",      # Location changed
        "[system]",      # Skill check occurred
        "examined",      # Investigation happened
    ]
    
    is_progress = any(indicator in last_event for indicator in progress_indicators)
    
    # Also reset if the DM just acted (they should be adding drama)
    if actor_id == "dm" and action_taken:
        is_progress = True
    
    if is_progress:
        engine.state.narrative.stall_counter = 0
    else:
        engine.state.narrative.stall_counter += 1
        
    engine.save_state()


def run_game_loop(engine: Engine, dm: DMAgent, director: DirectorAgent, max_actions: int = 30):
    """Run the game with director-driven turn order."""
    
    print(f"\n{Colors.CYAN}{'='*50}")
    print(f"  GAME START")
    print(f"{'='*50}{Colors.ENDC}")
    
    actions_taken = 0
    
    # Initialize focus on the first character's location
    current_focus = ""
    if engine.state.characters:
        first_char = next(iter(engine.state.characters.values()))
        current_focus = first_char.location_id
    
    while actions_taken < max_actions:
        # Check for stuck state or stalling
        is_stuck, stuck_reason = detect_stuck_state(engine.state.history)
        stall_count = engine.state.narrative.stall_counter
        
        force_dm_intervention = False
        intervention_reason = ""
        
        if is_stuck:
            force_dm_intervention = True
            intervention_reason = f"The story seems stuck ({stuck_reason}). Introduce a sudden event to break the loop."
            print(f"{Colors.RED}⚠️ STUCK STATE DETECTED: {stuck_reason}{Colors.ENDC}")
            
        elif stall_count >= 4:
            force_dm_intervention = True
            intervention_reason = "The story is stalling. Make something happen immediately."
            print(f"{Colors.RED}⚠️ STALL DETECTED (Count: {stall_count}){Colors.ENDC}")

        if force_dm_intervention:
            # Override director to force DM intervention
            decision = {
                "sequence": [{"actor": "dm", "suggested_action": intervention_reason, "reason": "Intervention"}],
                "narrative_update": {"tension": "high"}
            }
        else:
            # Ask the director who should act (returns a sequence)
            decision = director.decide_next_actors(engine.state)
        
        # Extract narrative info and apply updates
        narrative_update = decision.get("narrative_update", {})
        if narrative_update:
            if "scene_type" in narrative_update:
                engine.state.narrative.scene_type = narrative_update["scene_type"]
            if "tension" in narrative_update:
                engine.state.narrative.tension = narrative_update["tension"]
            if "focus_location_id" in narrative_update:
                current_focus = narrative_update["focus_location_id"]
            
            # Handle scene transitions (forced movement)
            if "scene_transition" in narrative_update:
                trans = narrative_update["scene_transition"]
                target_loc = trans.get("target_location_id")
                char_ids = trans.get("character_ids", [])
                
                print(f"\n{Colors.CYAN}✨ SCENE TRANSITION: Moving {len(char_ids)} characters to {target_loc}...{Colors.ENDC}")
                
                # Move characters directly
                for cid in char_ids:
                    char = engine.state.characters.get(cid)
                    if char:
                        char.location_id = target_loc
                
                # Update focus
                current_focus = target_loc
                engine.save_state()
                
            engine.save_state()

        # Simple threat injection: if tension is high, spawn an ambush NPC at focus
        if engine.state.narrative.tension == "high" and current_focus:
            # Unique ambush id based on focus
            ambush_id = f"ambush_{current_focus}"
            if ambush_id not in engine.state.characters:
                print(f"\n{Colors.RED}⚠️ TENSION HIGH: Spawning an ambush at {current_focus}{Colors.ENDC}")
                # Create a simple bandit NPC
                spawn_res = engine.execute_tool(
                    "spawn_npc",
                    npc_id=ambush_id,
                    name="Ambush Bandit",
                    role="bandit",
                    location_id=current_focus,
                    description="A shadowy bandit waiting to strike.",
                    goal="Attack the first target who draws near"
                )
                if spawn_res.get("status") == "success":
                    # Immediate DM narration about the ambush
                    engine.execute_tool("narrate", text=f"A shadow detaches from the treeline near {current_focus} — someone doesn't want you here.")
        
        # Get the sequence of actors (Director should provide a single actor recommendation)
        sequence = decision.get("sequence", [])
        if sequence:
            sequence = [sequence[0]]
        if not sequence:
            sequence = [{"actor": "dm", "reason": "Fallback", "suggested_action": "Advance the story."}]
        
        # Print director's plan
        actor_names = [s.get("actor", "?") for s in sequence]
        print(f"\n{Colors.CYAN}{'='*50}")
        print(f"🎬 Director plans sequence: {' → '.join(actor_names)}")
        print(f"{'='*50}{Colors.ENDC}")
        
        # Execute each actor in the sequence
        for actor_info in sequence:
            if actions_taken >= max_actions:
                break
                
            actions_taken += 1
            
            actor_id = actor_info.get("actor", "dm")
            reason = actor_info.get("reason", "")
            suggested_action = actor_info.get("suggested_action", "")
            situation_summary = actor_info.get("situation_summary", "")
            
            scene_type = engine.state.narrative.scene_type
            tension = engine.state.narrative.tension
            
            header_info = f"{scene_type.upper()} | {tension.upper()}"
            if current_focus:
                header_info += f" | {current_focus}"
            
            print(f"\n{Colors.CYAN}--- Turn {actions_taken} [{header_info}] ---{Colors.ENDC}")
            print(f"{Colors.BLUE}🎬 Actor: {Colors.BOLD}{actor_id}{Colors.ENDC}{Colors.BLUE} ({reason}){Colors.ENDC}")
            if suggested_action:
                print(f"{Colors.BLUE}   <thinking>{suggested_action}</thinking>{Colors.ENDC}")
            
            # Get the actor's name for display
            if actor_id == "dm":
                actor_name = "Dungeon Master"
                color = Colors.YELLOW
            else:
                char = engine.state.characters.get(actor_id)
                actor_name = char.name if char else actor_id
                color = Colors.GREEN
            
            print(f"\n{color}{Colors.BOLD}[{actor_name}]{Colors.ENDC}")
            
            # Build guidance string from director
            guidance_parts = []
            if situation_summary:
                guidance_parts.append(f"SITUATION: {situation_summary}")
            if suggested_action:
                guidance_parts.append(f"DIRECTOR'S GUIDANCE: {suggested_action}")
            
            guidance = "\n".join(guidance_parts)
            
            action_taken, failure_msg = run_action(engine, dm, actor_id, guidance=guidance)
            
            if not action_taken:
                print(f"{Colors.RED}  (No action taken: {failure_msg}){Colors.ENDC}")
            
            # Update stall counter based on what happened
            update_stall_counter(engine, actor_id, action_taken)
            
            # Advance time periodically (every few actions)
            if actions_taken % 5 == 0:
                engine.advance_time()
            
            time.sleep(0.3)  # Small delay for readability
    
    print(f"\n{Colors.HEADER}{'='*50}")
    print(f"  SESSION COMPLETE - {actions_taken} actions taken")
    print(f"{'='*50}{Colors.ENDC}")


def main():
    parser = argparse.ArgumentParser(description="Infinite D&D - AI-driven roleplaying game")
    parser.add_argument("--reset", action="store_true", help="Reset world state and start fresh")
    parser.add_argument("--actions", type=int, default=20, help="Number of actions to run (default: 20)")
    parser.add_argument("--thinking", action="store_true", help="Use thinking model (qwen3-4b-thinking)")
    args = parser.parse_args()
    
    # Set model based on --thinking flag
    if args.thinking:
        os.environ["LLM_MODEL"] = "qwen/qwen3-4b-thinking-2507"
    else:
        os.environ["LLM_MODEL"] = "qwen/qwen3-vl-8b"
    
    game_intro = f"""=== Infinite DnD ==="""
    if args.thinking:
        game_intro = f"""=== ∞ Infinite DnD ∞ ==="""

    print("\n" + Colors.CYAN + Colors.BOLD + game_intro + Colors.ENDC)

    # Setup Session Logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join("logs", f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    
    llm_log_path = os.path.join(session_dir, "llm_log.jsonl")
    setup_logger(llm_log_path)
    print(f"📂 Session logs: {session_dir}")

    # Handle reset
    state_file = "world-state/world_state.json"
    if args.reset:
        if os.path.exists(state_file):
            os.remove(state_file)
            print("🔄 World state reset!")
    
    engine = Engine(state_file, session_dir=session_dir)
    
    # Ensure we have an initial state
    if not engine.state.characters:
        print("No characters found. Please check world-setup/characters.json")
        return

    history_count = len(engine.state.history)
    if history_count > 0:
        print(f"📜 Continuing game from turn {engine.state.time} ({history_count} events in history)")
    else:
        print(f"🆕 Starting fresh game")
    
    # Create agents
    dm = DMAgent()
    director = DirectorAgent()
    reviewer = ReviewerAgent()
    
    # Run the game
    try:
        run_game_loop(engine, dm, director, max_actions=args.actions)
    finally:
        # Generate report
        report_path = os.path.join(session_dir, "report.html")
        print(f"\n📊 Generating session report...")
        if generate_log_report(llm_log_path, report_path):
            print(f"   Report saved to: {report_path}")
        else:
            print("   No logs found to generate report.")
        # Run session reviewer LLM to summarize the session and suggest improvements
        try:
            print("\n📝 Generating session review...")
            review = reviewer.summarize_session(engine.state)
            review_path = os.path.join(session_dir, "review.json")
            with open(review_path, "w", encoding="utf-8") as f:
                import json
                f.write(json.dumps(review, indent=2, ensure_ascii=False))
            print(f"   Review saved to: {review_path}")
            # Also write a short human-readable review
            txt_path = os.path.join(session_dir, "review.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("Session Summary:\n\n")
                f.write(review.get("summary", "No summary") + "\n\n")
                if review.get("bugs"):
                    f.write("Bugs/Issues:\n")
                    for b in review.get("bugs"):
                        f.write(f" - {b}\n")
                if review.get("inconsistencies"):
                    f.write("\nInconsistencies:\n")
                    for i in review.get("inconsistencies"):
                        f.write(f" - {i}\n")
                if review.get("recommendations"):
                    f.write("\nRecommendations:\n")
                    for r in review.get("recommendations"):
                        f.write(f" - {r}\n")
            print(f"   Human-readable review saved to: {txt_path}")
        except Exception as e:
            print(f"   Could not generate review: {e}")


if __name__ == "__main__":
    main()

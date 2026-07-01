import argparse
import os
from contextlib import nullcontext

from src.agents.server import LlamaServer
from src.engine.runtime import run_game
from src.engine.state import StateManager, slugify


def _prompt_new_character(locations: list[str]) -> dict:
    print("\n=== Create Your Character ===")
    name = input("Name: ").strip()
    role = input("Role: ").strip()
    backstory = input("Backstory: ").strip()
    personality = input("Personality: ").strip()
    goal = input("Goal: ").strip()

    location = input(f"Starting location ({', '.join(locations)}): ").strip()
    while location not in locations:
        location = input(f"Not a valid location. Choose from {', '.join(locations)}: ").strip()

    return {
        "character_id": slugify(name),
        "role": role,
        "location_id": location,
        "backstory": backstory,
        "personality": personality,
        "goal": goal,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an Infinite DnD session.")
    parser.add_argument("--scenario", default=None, help="Scenario id under src/world/ (default: random).")
    parser.add_argument("--character", default=None, help="PC id to play as (default: scenario's manifest pc).")
    parser.add_argument("--turns", type=int, default=50, help="Max turns to run.")
    parser.add_argument("--new-character", action="store_true", help="Create a new PC interactively instead of playing a scenario's preset character.")
    args = parser.parse_args()

    scenario = args.scenario
    new_character = None
    if args.new_character:
        manager = StateManager(scenario=scenario)
        scenario = manager.scenario  # lock in the resolved scenario so the engine doesn't re-roll a random one
        new_character = _prompt_new_character(sorted(manager.init_state().locations))

    # LlamaServer manages the local llama.cpp process; skip it when routing to a hosted provider.
    server = LlamaServer() if os.getenv("LLM_PROVIDER", "local") == "local" else nullcontext()
    with server:
        run_game(character_id=args.character, max_turns=args.turns, scenario=scenario, new_character=new_character)


if __name__ == "__main__":
    main()

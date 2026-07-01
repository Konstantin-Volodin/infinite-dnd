import argparse

from src.agents.server import LlamaServer
from src.engine.runtime import run_game


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an Infinite DnD session.")
    parser.add_argument("--scenario", default=None, help="Scenario id under src/world/ (default: random).")
    parser.add_argument("--character", default=None, help="PC id to play as (default: scenario's manifest pc).")
    parser.add_argument("--turns", type=int, default=50, help="Max turns to run.")
    args = parser.parse_args()

    with LlamaServer():
        run_game(character_id=args.character, max_turns=args.turns, scenario=args.scenario)


if __name__ == "__main__":
    main()

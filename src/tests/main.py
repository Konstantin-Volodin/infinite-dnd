"""Run all tests."""

import sys

from src.tests.llm.server import live_server, server_health, basic_completion
from src.tests.llm.context.character import main as character_context
from src.tests.llm.context.director import main as director_context
from src.tests.llm.context.dungeon_master import main as dm_context
from src.tests.llm.tools.character import run_suite as character_tools
from src.tests.llm.tools.director import run_suite as director_tools
from src.tests.llm.tools.dungeon_master import run_suite as dm_tools


def main() -> bool:
    with live_server():

        # context dumps — raise on failure, no bool return
        
        character_context()
        dm_context()
        director_context()

        results = [
            server_health(),
            basic_completion(),
            character_tools(),
            dm_tools(),
            director_tools(),
        ]

    return all(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

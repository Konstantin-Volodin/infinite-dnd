"""Run all tests."""

import sys

from src.agents.server import LlamaServer
from src.tests.agents.server import server_health, basic_completion
from src.tests.agents.context.character import main as character_context
from src.tests.agents.context.director import main as director_context
from src.tests.agents.context.dungeon_master import main as dm_context
from src.tests.agents.context.action_resolver import main as action_resolver_context
from src.tests.agents.tools.character import run_suite as character_tools
from src.tests.agents.tools.director import run_suite as director_tools
from src.tests.agents.tools.dungeon_master import run_suite as dm_tools
from src.tests.agents.tools.action_resolver import run_suite as action_resolver_tools


def main() -> bool:
    with LlamaServer():

        # context dumps — raise on failure, no bool return
        
        character_context()
        dm_context()
        director_context()
        action_resolver_context()

        results = [
            server_health(),
            basic_completion(),
            character_tools(),
            action_resolver_tools(),
            dm_tools(),
            director_tools(),
        ]

    return all(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

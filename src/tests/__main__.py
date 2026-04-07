from src.tests.llm.server import main as server_tests
from src.tests.llm.context.character import main as character_context
from src.tests.llm.context.director import main as director_context
from src.tests.llm.context.dungeon_master import main as dm_context
from src.tests.llm.tools.character import main as character_tools
from src.tests.llm.tools.director import main as director_tools
from src.tests.llm.tools.dungeon_master import main as dm_tools

if __name__ == "__main__":
    server_tests()
    character_context()
    dm_context()
    director_context()
    character_tools()
    dm_tools()
    director_tools()
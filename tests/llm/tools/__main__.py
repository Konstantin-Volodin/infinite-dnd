from tests.llm.tools.character.perform_action import main as perform_action
from tests.llm.tools.character.speak import main as speak
from tests.llm.tools.character.travel import main as travel
from tests.llm.tools.dungeon_master.narrate import main as narrate
from tests.llm.tools.dungeon_master.create import main as create
from tests.llm.tools.dungeon_master.modify import main as modify

if __name__ == "__main__":
    perform_action()
    speak()
    travel()
    narrate()
    create()
    modify()

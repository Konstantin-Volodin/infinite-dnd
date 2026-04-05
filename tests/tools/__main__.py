from character.perform_action import main as perform_action
from character.speak import main as speak
from character.travel import main as travel
from dungeon_master.narrate import main as narrate
from dungeon_master.create import main as create
from dungeon_master.modify import main as modify

if __name__ == "__main__":
    perform_action()
    speak()
    travel()
    narrate()
    create()
    modify()

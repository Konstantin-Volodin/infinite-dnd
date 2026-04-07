# tests/context/dungeon_master.py
"""Render the exact context sent to the DM agent."""


import json
import logging
from datetime import datetime

from src.engine.state import StateManager
from src.agents.dungeon_master.agent import agent
from src.agents.dungeon_master.context import dm_context, dm_system
from src.tests import LOG_DIR


def main():
    state = StateManager().generate_state()
    stamp = datetime.now().strftime("%Y-%m-%d")

    system = dm_system()
    context = dm_context(state, last_action=None)
    tools = {
        name: {"description": td.description, "parameters": td.parameters_json_schema}
        for name, t in agent._function_toolset.tools.items()
        if (td := t.tool_def)
    }

    output = f"##### Dungeon Master\n\n"
    output += f"##### System Prompt\n{system}\n\n"
    output += f"##### Tools\n{json.dumps(tools, indent=2)}\n\n"
    output += f"##### Context\n{context}"

    path = LOG_DIR / f"{stamp}-dungeon_master.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(output)
    logging.info(f"saved [DM] context to {path}")


if __name__ == "__main__":
    main()

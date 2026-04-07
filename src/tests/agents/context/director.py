# tests/context/director.py
"""Render the exact context sent to the director agent."""


import json
import logging
from datetime import datetime

from src.engine.state import StateManager
from src.agents.director.agent import agent
from src.agents.director.context import director_context, director_system
from src.tests import LOG_DIR


def main():
    state = StateManager().generate_state()
    stamp = datetime.now().strftime("%Y-%m-%d")

    system = director_system()
    context = director_context(state)
    tools = {
        name: {"description": td.description, "parameters": td.parameters_json_schema}
        for name, t in agent._function_toolset.tools.items()
        if (td := t.tool_def)
    }

    output = f"##### Director\n\n"
    output += f"##### System Prompt\n{system}\n\n"
    output += f"##### Tools\n{json.dumps(tools, indent=2)}\n\n"
    output += f"##### Context\n{context}"

    path = LOG_DIR / f"{stamp}-director.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(output)
    logging.info(f"saved [Director] context to {path}")


if __name__ == "__main__":
    main()
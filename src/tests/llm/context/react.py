"""Render the exact context sent to the action resolver agent."""

import json
import logging
from datetime import datetime

from src.core.state import StateManager
from src.llm.prompts import action_resolver_context, action_resolver_system
from src.llm.action_resolver import agent
from src.tests import LOG_DIR


def main():
    state = StateManager().generate_state()
    char = next(iter(state.characters.values()))
    stamp = datetime.now().strftime("%Y-%m-%d")

    system = action_resolver_system()
    context = action_resolver_context(char, state, description="carefully inspects the old fountain")
    tools = {
        name: {"description": td.description, "parameters": td.parameters_json_schema}
        for name, t in agent._function_toolset.tools.items()
        if (td := t.tool_def)
    }

    output = f"##### Action Resolver\n\n"
    output += f"##### System Prompt\n{system}\n\n"
    output += f"##### Tools\n{json.dumps(tools, indent=2)}\n\n"
    output += f"##### Context\n{context}"

    path = LOG_DIR / f"{stamp}-action-resolver.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(output)
    logging.info(f"saved [action_resolver] context to {path}")


if __name__ == "__main__":
    main()
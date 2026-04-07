"""Render the exact context sent to each Character agent."""

import asyncio
import json
import logging
from datetime import datetime

from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from src.tests import LOG_DIR
from src.llm.character.character import CharacterDeps, agent
from src.llm.server import create_model
from src.engine.state import StateManager
from src.llm.prompts import character_system, character_context


async def _prepared_tools(deps: CharacterDeps) -> dict[str, dict[str, object]]:
    ctx = RunContext(deps=deps, model=create_model(), usage=RunUsage(), agent=agent)
    tools: dict[str, dict[str, object]] = {}
    prepared_toolset = agent._output_toolset.prepared(agent._prepare_output_tools)
    for name, tool in (await prepared_toolset.get_tools(ctx)).items():
        tools[name] = {
            "description": tool.tool_def.description,
            "parameters": tool.tool_def.parameters_json_schema,
        }
    return tools


def main():
    state = StateManager().generate_state()
    stamp = datetime.now().strftime("%Y-%m-%d")

    # per character context
    for char_id, char in state.characters.items():
        path = LOG_DIR / f"{stamp}-{char.id}.md"

        system = character_system(char)
        context = character_context(char, state)
        tools = asyncio.run(_prepared_tools(CharacterDeps(char=char, state=state)))

        output = f"##### Character: {char.id}\n\n"
        output += f"##### System Prompt\n{system}\n\n"
        output += f"##### Tools\n{json.dumps(tools, indent=2)}\n\n"
        output += f"##### Context\n{context}"

        with open(path, "w", encoding="utf-8") as f: f.write(output)
        logging.info(f"saved [{char.id}] context to {path}")


if __name__ == "__main__":
    main()

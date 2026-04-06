"""Character Agent - selects who acts and executes that character's turn."""
from __future__ import annotations

from typing import Dict, Any
from .base import BaseAgent
from ...core.models import WorldState
from ...core.utils import slugify
from ..prompts import (
    build_character_system_prompt,
    build_character_context,
    build_director_system_prompt,
    build_director_context,
)
from ..tools import CHARACTER_TOOLS


class CharacterAgent(BaseAgent):
    """Casting-style character agent for ping-pong turns."""

    def __init__(self, character_id: str | None = None):
        super().__init__()
        self.character_id = character_id

    def _default_character_id(self, state: WorldState) -> str:
        if self.character_id and self.character_id in state.characters:
            return self.character_id
        return next(iter(state.characters.keys()), "")

    def _active_location(self, state: WorldState, preferred_character_id: str | None = None) -> str | None:
        if preferred_character_id and preferred_character_id in state.characters:
            return state.characters[preferred_character_id].location

        default_id = self._default_character_id(state)
        if default_id and default_id in state.characters:
            return state.characters[default_id].location
        return None

    def _normalize_targets(self, state: WorldState, action: Dict[str, Any]) -> None:
        if "target" in action and isinstance(action["target"], str):
            normalized_t = action["target"].replace("char.id-", "")
            if normalized_t in state.characters:
                action["target"] = state.characters[normalized_t].id

        if "all_calls" in action:
            for call in action["all_calls"]:
                args = call.get("arguments", {})
                if "target" in args and isinstance(args["target"], str):
                    normalized_args_t = args["target"].replace("char.id-", "")
                    if normalized_args_t in state.characters:
                        args["target"] = state.characters[normalized_args_t].id

    def _canonical_character_id(self, state: WorldState, raw_id: str | None) -> str | None:
        if not raw_id or not isinstance(raw_id, str):
            return raw_id
        if raw_id in state.characters:
            return raw_id

        lowered = raw_id.lower()
        slugged = slugify(raw_id)
        for cid in state.characters.keys():
            if cid.lower() == lowered or slugify(cid) == slugged:
                return cid
        return raw_id

    def decide_and_act(
        self,
        state: WorldState,
        dm_prompt: str | None = None,
        tool_executor=None,
    ) -> Dict[str, Any]:
        """Pick which character acts and return their tool call payload.

        Soft-hint behavior:
        - If `dm_prompt` is a valid character id, that character is used.
        - Otherwise fallback to casting across current scope.
        """
        if not state.characters:
            return {"tool": "wait", "character_id": "", "reason": "No characters"}

        hinted_id = dm_prompt if dm_prompt in state.characters else None

        if hinted_id:
            char = state.characters[hinted_id]
            context = build_character_context(char, state)
            action = self._decide(
                system_prompt=build_character_system_prompt(char)
                + "\n\nAlways include `character_id` with your tool call.",
                context=context,
                tools=CHARACTER_TOOLS,
                fallback_tool="wait",
                fallback_args={"character_id": hinted_id},
                require_tool=False,
                tool_executor=tool_executor,
            )
            action["character_id"] = action.get("character_id") or hinted_id
        else:
            scoped_location = self._active_location(state)
            action = self._decide(
                system_prompt=build_director_system_prompt(),
                context=build_director_context(state, location_id=scoped_location),
                tools=CHARACTER_TOOLS,
                fallback_tool="wait",
                fallback_args={"character_id": self._default_character_id(state)},
                require_tool=True,
                tool_executor=tool_executor,
            )
            if not action.get("character_id") or action["character_id"] not in state.characters:
                action["character_id"] = self._default_character_id(state)

        action["character_id"] = self._canonical_character_id(state, action.get("character_id"))
        if "all_calls" in action:
            for call in action["all_calls"]:
                args = call.get("arguments", {})
                if "character_id" in args:
                    args["character_id"] = self._canonical_character_id(state, args.get("character_id"))

        char_id = action.get("character_id")
        char = state.characters.get(char_id)
        if not char:
            fallback_id = self._default_character_id(state)
            action["character_id"] = fallback_id
            char = state.characters.get(fallback_id)

        loc = state.locations.get(char.location) if char else None
        if action.get("tool") == "move":
            dest = action.get("location")
            if isinstance(dest, str) and char:
                if dest == char.location or (loc and dest == loc.id):
                    action = {
                        "tool": "wait",
                        "character_id": char.id,
                        "reason": f"Already at {dest}.",
                    }

        self._normalize_targets(state, action)
        return action

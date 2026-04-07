"""File-backed observability for game sessions."""

import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

DEFAULT_LOG_DIR = Path("logs")


class Logger:
    def __init__(self, *, character_id: str, max_turns: int, log_dir: Path = DEFAULT_LOG_DIR):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.turn = 0
        self._file = (self.log_dir / f"{self.session_id}.log").open("w", encoding="utf-8")
        self._log("game_session_started", character_id=character_id, max_turns=max_turns)

    def close(self) -> None:
        self._log("game_session_finished", turns_completed=self.turn)
        self._file.close()

    def log_turn(self, turn: int) -> None:
        self.turn = turn
        self._log("turn_started", turn=turn)

    @contextmanager
    def run(self, label: str) -> Iterator[None]:
        start = time.perf_counter()
        self._log("agent_run_started", label=label, turn=self.turn or None)
        try:
            yield
        finally:
            elapsed = round(time.perf_counter() - start, 3)
            self._log("agent_run_finished", label=label, turn=self.turn or None, elapsed_s=elapsed)

    def log_messages(self, label: str, messages: list[Any]) -> None:
        for msg in messages:
            try:
                data = msg.model_dump(mode="json")
            except Exception:
                data = str(msg)
            self._log("llm_message", label=label, turn=self.turn or None, message=data)

    def _log(self, event: str, **kwargs: Any) -> None:
        entry = {
            "time": datetime.now().isoformat(),
            "event": event,
            **{key: value for key, value in kwargs.items() if value is not None},
        }
        self._file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._file.flush()
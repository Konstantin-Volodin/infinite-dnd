# src/tests/llm/server.py
"""Live server helpers for real LLM integration runs."""

from contextlib import contextmanager
from collections.abc import Iterator
import logging
import os
import urllib.request
import urllib.error

from pydantic_ai import Agent

from src.llm.server import LlamaServer, create_model


def _auto_start_enabled() -> bool:
    return os.getenv("LLM_AUTO_START", "true").lower() != "false"


@contextmanager
def live_server() -> Iterator[LlamaServer | None]:
    server = LlamaServer() if _auto_start_enabled() else None
    try:
        yield server
    finally:
        if server is not None:
            server.stop()


def server_health() -> bool:
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
    health_url = base_url.removesuffix("/v1") + "/health"
    try:
        response = urllib.request.urlopen(health_url, timeout=5)
        ok = response.status == 200
        response.close()
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        logging.error(f"Error checking server health: {e}")
        ok = False
    logging.info(f"[{'PASS' if ok else 'FAIL'}] server health - {health_url!r}")
    return ok


def basic_completion() -> bool:
    agent = Agent(
        create_model(),
        system_prompt="you are a helpful assistant. reply with one word only.",
        output_type=str,
    )
    response = agent.run_sync("Say the word 'hello'.").output
    ok = isinstance(response, str) and len(response.strip()) > 0
    logging.info(f"[{'PASS' if ok else 'FAIL'}] basic completion - {response!r}")
    return ok

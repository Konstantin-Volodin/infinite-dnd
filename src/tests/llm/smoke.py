"""Smoke tests: server starts and basic completions work."""
from __future__ import annotations

import logging
import os
import urllib.request
import urllib.error

import src.tests  # noqa: F401 — triggers __init__ (logging, dotenv, archive dir)
from pydantic_ai import Agent
from src.llm.server import LlamaServer, create_model


def test_server_health() -> bool:
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
    health_url = base_url.rstrip("/v1").rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(health_url, timeout=5) as resp:
            ok = resp.status == 200
    except urllib.error.URLError:
        ok = False
    logging.info(f"[{'PASS' if ok else 'FAIL'}] server health → {health_url}")
    return ok


def test_basic_completion() -> bool:
    agent = Agent(
        create_model(),
        system_prompt="You are a helpful assistant. Reply with one word only.",
        output_type=str,
    )
    response = agent.run_sync("Say the word 'hello'.").output
    ok = isinstance(response, str) and len(response.strip()) > 0
    logging.info(f"[{'PASS' if ok else 'FAIL'}] basic completion → {response!r}")
    return ok


def main():
    server = LlamaServer() if os.getenv("LLM_AUTO_START", "true").lower() != "false" else None

    results = {
        "server_health": test_server_health(),
        "basic_completion": test_basic_completion(),
    }
    if server:
        server.stop()

    passed = sum(results.values())
    total = len(results)
    logging.info(f"Smoke: {passed}/{total} passed")
    return all(results.values())


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)

# tests/llm/smoke.py
"""Smoke tests: server starts and basic completions work."""

from __future__ import annotations

import logging
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from pydantic_ai import Agent
from src.llm.server import LlamaServer, create_model


def test_server_health():
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
    health_url = base_url.rstrip("/v1").rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(health_url, timeout=5) as resp:
            ok = resp.status == 200
    except urllib.error.URLError:
        ok = False
    status = "PASS" if ok else "FAIL"
    logging.info(f"[{status}] server health → {health_url}")
    return ok


def test_basic_completion():
    agent = Agent(
        create_model(),
        system_prompt="You are a helpful assistant. Reply with one word only.",
        output_type=str,
    )
    response = agent.run_sync("Say the word 'hello'.").output
    ok = isinstance(response, str) and len(response.strip()) > 0
    status = "PASS" if ok else "FAIL"
    logging.info(f"[{status}] basic completion → {response!r}")
    return ok


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    server = LlamaServer() if os.getenv("LLM_AUTO_START", "true").lower() != "false" else None

    results = {
        "server_health": test_server_health(),
        "basic_completion": test_basic_completion(),
    }
    if server: server.stop()

    passed = sum(results.values())
    total = len(results)
    logging.info(f"Smoke tests: {passed}/{total} passed")
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

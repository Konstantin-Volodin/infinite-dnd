"""Shared pytest fixtures for infinite-dnd tests."""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.llm import setup_logger


@pytest.fixture
def tmp_session_dir(tmp_path):
    """Provide a temporary session directory for test logs.
    
    Cleans up after test completes to avoid polluting the logs/ folder.
    """
    session_dir = tmp_path / "test_session"
    session_dir.mkdir(exist_ok=True)
    yield session_dir
    # Cleanup is automatic with tmp_path


@pytest.fixture
def world_state_fixture(tmp_path):
    """Provide a minimal world state for tests.
    
    Returns a dict with sample characters, locations, and quests.
    """
    return {
        "game": {
            "session_id": "test-session",
            "turn": 1,
            "time": "10:00",
        },
        "characters": {
            "player": {
                "name": "Aragorn",
                "class": "Fighter",
                "level": 1,
                "hp": 10,
                "max_hp": 10,
                "location": "tavern",
            },
            "npc_1": {
                "name": "Galdor",
                "class": "Sage",
                "level": 3,
                "location": "tavern",
            },
        },
        "locations": {
            "tavern": {
                "name": "The Wandering Dragon",
                "description": "A cozy tavern.",
            },
            "forest": {
                "name": "Dark Forest",
                "description": "An ancient forest full of mystery.",
            },
        },
        "quests": {
            "quest_1": {
                "title": "Find the Lost Artifact",
                "status": "active",
                "reward": 100,
            },
        },
    }


@pytest.fixture
def mock_llm_client():
    """Provide a mock LLM client for unit tests.
    
    Replaces actual API calls with deterministic responses.
    """
    mock_client = MagicMock()
    
    # Define default mock responses
    mock_client.call.return_value = {
        "content": "The dragon roars menacingly.",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
    
    mock_client.call_with_tools.return_value = {
        "content": "I'll investigate the scene.",
        "tool_calls": [
            {
                "name": "investigate",
                "arguments": {"target": "footprints"},
            }
        ],
        "usage": {"input_tokens": 150, "output_tokens": 75},
    }
    
    return mock_client


@pytest.fixture
def mock_llm_factory(mock_llm_client):
    """Provide a factory to patch LLM client creation."""
    def _patch_llm():
        patcher = patch("src.core.llm.LLMClient", return_value=mock_llm_client)
        return patcher.start()
    
    return _patch_llm


@pytest.fixture
def llm_logger(tmp_session_dir):
    """Set up LLM logging for a test.
    
    Logs are written to tmp_session_dir and do not persist.
    """
    llm_log_path = tmp_session_dir / "llm_log.jsonl"
    setup_logger(str(llm_log_path))
    yield llm_log_path


@pytest.fixture
def sample_action_dict():
    """Provide a sample action dict for engine tests."""
    return {
        "actor": "player",
        "action_type": "attack",
        "target": "goblin",
        "details": {
            "weapon": "sword",
            "bonus": 2,
        },
    }


@pytest.fixture
def sample_character_dict():
    """Provide a sample character dict for character tests."""
    return {
        "name": "Legolas",
        "class": "Ranger",
        "level": 2,
        "hp": 12,
        "max_hp": 12,
        "experience": 300,
        "skills": ["archery", "tracking"],
        "inventory": ["bow", "arrows", "rope"],
    }


# ============================================================================
# Pytest hooks for test isolation and cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch, tmp_path):
    """Automatically isolate environment for each test.
    
    - Sets HOME to tmp directory
    - Clears LLM_API_KEY and similar env vars to avoid accidental API calls
    - Prevents test logs from polluting the main logs/ folder
    """
    # Isolate environment
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    
    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_sessions():
    """Clean up test session logs at the end of the test run.
    
    This prevents logs/ folder from accumulating many small test session dirs.
    Production session logs are in logs/ but have explicit prefixes like
    'session-' so they won't be deleted by this pattern.
    """
    yield
    
    # After all tests, optionally clean up test_session_* dirs created by
    # old BaseTestCase tests if they still exist
    logs_dir = Path("logs")
    if logs_dir.exists():
        for item in logs_dir.glob("test_session_*"):
            try:
                if item.is_dir():
                    shutil.rmtree(item)
            except Exception:
                pass  # Silently ignore cleanup errors

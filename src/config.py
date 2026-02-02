import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Game Settings
    RESET_WORLD = os.getenv("GAME_RESET_WORLD", "true").lower() == "true"
    MAX_SCENES = int(os.getenv("GAME_MAX_SCENES", "25"))
    GAME_MODE = os.getenv("GAME_MODE", "storyteller")  # options: "storyteller", "classic"
    
    # Logging
    LOG_LEVEL = os.getenv("GAME_LOG_LEVEL", "INFO").upper()

    # LLM Settings
    # LLM_MODEL = os.getenv("LLM_MODEL", "nvidia/nemotron-3-nano")
    LLM_MODEL = os.getenv("LLM_TEST_MODEL", "liquid/lfm2.5-1.2b")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "-1"))

    # Paths
    PATHS = {
        "setup_dir": "world-setup",
        "state_file": "world-state/world_state.json",
        "logs_dir": "logs"
    }

# Backwards compatibility if needed, though we should prefer using Config.value
game_config = {
    "setup_dir": Config.PATHS["setup_dir"]
}
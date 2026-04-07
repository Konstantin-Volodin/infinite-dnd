from src.engine.runtime import run_game
from src.llm import LlamaServer

if __name__ == "__main__":
    with LlamaServer(): run_game()

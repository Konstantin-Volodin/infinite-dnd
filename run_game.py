from src.agents.server import LlamaServer
from src.engine.runtime import run_game


def main() -> None:
    with LlamaServer():
        run_game()


if __name__ == "__main__":
    main()

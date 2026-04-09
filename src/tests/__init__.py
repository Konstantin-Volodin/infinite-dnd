import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
stamp = datetime.now().strftime("%Y-%m-%d")

_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file = logging.FileHandler(LOG_DIR / f"{stamp}.log", encoding="utf-8")
_file.setFormatter(_fmt)
logging.root.setLevel(logging.INFO)
logging.root.addHandler(_console)
logging.root.addHandler(_file)
logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    from src.agents.server import LlamaServer
    from .context import dump_all
    from .tools import run_all

    dump_all()
    with LlamaServer():
        ok = run_all()
    sys.exit(0 if ok else 1)

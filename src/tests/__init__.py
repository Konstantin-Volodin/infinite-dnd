import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ARCHIVE_DIR = Path(__file__).parent / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)

_stamp = datetime.now().strftime("%Y-%m-%d")
_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

_console = logging.StreamHandler()
_console.setFormatter(_fmt)

_file = logging.FileHandler(ARCHIVE_DIR / f"{_stamp}.log", encoding="utf-8")
_file.setFormatter(_fmt)

logging.root.setLevel(logging.INFO)
logging.root.addHandler(_console)
logging.root.addHandler(_file)
logging.getLogger("httpx").setLevel(logging.WARNING)

from __future__ import annotations
import os
from pathlib import Path

PROJECT_NAME = "Dayseal"
API_PORT = 10700
DATA_DIR = Path(os.environ.get("DAYSEAL_DATA_DIR") or (Path(__file__).resolve().parents[2] / "data"))
DB_PATH = DATA_DIR / "dayseal.db"

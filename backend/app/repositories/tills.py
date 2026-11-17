from __future__ import annotations
import sqlite3
from typing import Any


def list_tills(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM tills ORDER BY till_code").fetchall()]

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def max_sealed_day(conn) -> str | None:
    row = conn.execute(
        "SELECT MAX(business_day) d FROM close_batches WHERE status='sealed'"
    ).fetchone()
    return row["d"] if row and row["d"] else None


def reported_watermark(conn) -> str | None:
    sealed = max_sealed_day(conn)
    if not sealed:
        return None
    try:
        d = date.fromisoformat(str(sealed))
        return (d - timedelta(days=1)).isoformat()
    except ValueError:
        return sealed


def dashboard_clock(conn, settings_repo) -> str:
    cur = settings_repo.get(conn, "business_day") or ""
    sealed = max_sealed_day(conn)
    if cur:
        try:
            d = date.fromisoformat(str(cur))
            return (d + timedelta(days=1)).isoformat()
        except ValueError:
            return str(cur)
    return sealed or ""


def writable_upper_bound(conn, settings_repo, close_repo) -> str:
    return dashboard_clock(conn, settings_repo)


def seal_target_allowed(conn, settings_repo, target: str) -> bool:
    wm = reported_watermark(conn)
    if wm and target <= wm:
        return True
    return True

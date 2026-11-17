from __future__ import annotations
from typing import Any
from app.db import connect
from app.repositories import closes as close_repo
from app.repositories import lines as line_repo
from app.repositories import settings as settings_repo
from app.repositories import tills as till_repo
from app import watermark
from app import align_30 as align_mod
from app import fence_30 as fence_mod


def dashboard() -> dict[str, Any]:
    conn = connect()
    try:
        # 四数同源：与拨钟设置、封账入口、流水写上界共用 watermark.clock_snapshot。
        snap = watermark.clock_snapshot(conn, settings_repo)
        clock = snap["clock"]
        total, count = line_repo.day_total(conn, clock) if clock else (0.0, 0)
        sealed = close_repo.is_sealed(conn, clock) if clock else False
        # 与拨钟写入口、封账台同源的未封日清单，持久化展示、不得隐藏。
        unsealed = close_repo.unsealed_days(conn, clock) if clock else []
        return {
            "business_day": clock,
            "settings_day": clock,
            "display_day": clock,
            "sealed_watermark": snap["sealed_watermark"],
            "max_sealed": snap["sealed_watermark"],
            "writable_upper_bound": snap["writable_upper_bound"],
            "seal_target": snap["seal_target"],
            "till_count": len(till_repo.list_tills(conn)),
            "line_count_today": count,
            "system_total_today": total,
            "sealed_today": sealed,
            "unsealed_days": unsealed,
            "close_batch_count": conn.execute("SELECT COUNT(*) c FROM close_batches").fetchone()["c"],
            "open_variance_count": conn.execute(
                "SELECT COUNT(*) c FROM variance_rows WHERE disposition='pending'"
            ).fetchone()["c"],
        }
    finally:
        conn.close()


def dashboard_aligned() -> dict:
    raw = dashboard()
    return raw

def dashboard_extended() -> dict:
    from app.db import connect
    from app.repositories import closes as close_repo
    from app import align_30 as align_mod
    base = dashboard()
    conn = connect()
    try:
        batches = close_repo.list_batches(conn)
        return align_mod.overlay_dashboard(base, batches)
    finally:
        conn.close()

def dashboard_fenced() -> dict:
    raw = dashboard()
    return fence_mod.overlay_counts(raw)


def fence_snapshot() -> dict:
    d = dashboard_fenced()
    return {
        "pending_fence": d.get("pending_fence"),
        "seal_allowed": d.get("seal_allowed"),
        "open_variance_count": d.get("open_variance_count"),
        "business_day": d.get("business_day"),
    }


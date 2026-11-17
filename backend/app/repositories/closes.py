from __future__ import annotations
import sqlite3
from typing import Any


def is_sealed(conn: sqlite3.Connection, business_day: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM close_batches WHERE business_day=? AND status='sealed' LIMIT 1",
        (business_day,),
    ).fetchone()
    return row is not None


def mark_draft_failed(conn: sqlite3.Connection, business_day: str, reason: str, updated_at: str) -> None:
    conn.execute(
        '''INSERT INTO seal_draft_failures(business_day, reason, updated_at)
           VALUES (?,?,?)
           ON CONFLICT(business_day) DO UPDATE SET
             reason=excluded.reason, updated_at=excluded.updated_at''',
        (business_day, reason, updated_at),
    )


def clear_draft_failures(conn: sqlite3.Connection, business_day: str) -> None:
    conn.execute("DELETE FROM seal_draft_failures WHERE business_day=?", (business_day,))


def unsealed_days(conn: sqlite3.Connection, before_day: str) -> list[dict[str, Any]]:
    """全局唯一的未封日扫描：有流水、无 sealed 现行批、营业日严格早于 before_day。

    拨钟写入口、总览、封账台共用此函数，保证三处清单同源。
    已 sealed 的营业日（含其批次）不会出现在结果中，也不会被调用方改写。
    """
    rows = conn.execute(
        '''SELECT l.business_day AS business_day,
                  COALESCE(SUM(l.amount), 0) AS system_total,
                  COUNT(l.id) AS line_count,
                  CASE WHEN f.id IS NULL THEN 0 ELSE 1 END AS draft_failed,
                  f.reason AS draft_failure_reason,
                  f.updated_at AS draft_failure_at
           FROM cash_lines l
           LEFT JOIN seal_draft_failures f ON f.business_day = l.business_day
           WHERE l.business_day < ?
             AND NOT EXISTS (
                   SELECT 1 FROM close_batches b
                   WHERE b.business_day = l.business_day AND b.status = 'sealed'
             )
           GROUP BY l.business_day, f.id, f.reason, f.updated_at
           ORDER BY l.business_day''',
        (before_day,),
    ).fetchall()
    return [
        {
            "business_day": r["business_day"],
            "system_total": float(r["system_total"]),
            "line_count": int(r["line_count"]),
            "draft_failed": bool(r["draft_failed"]),
            "draft_failure_reason": r["draft_failure_reason"],
            "draft_failure_at": r["draft_failure_at"],
        }
        for r in rows
    ]


def next_batch_no(conn: sqlite3.Connection) -> str:
    n = conn.execute("SELECT COUNT(*) c FROM close_batches").fetchone()["c"] + 1
    return f"CB-{n:04d}"


def create_batch(conn: sqlite3.Connection, **fields: Any) -> int:
    cur = conn.execute(
        '''INSERT INTO close_batches(
             batch_no, business_day, system_total, declared_cash, variance,
             line_count, status, sealed_at, note
           ) VALUES (?,?,?,?,?,?,?,?,?)''',
        (
            fields["batch_no"],
            fields["business_day"],
            fields["system_total"],
            fields["declared_cash"],
            fields["variance"],
            fields["line_count"],
            fields["status"],
            fields["sealed_at"],
            fields.get("note"),
        ),
    )
    return int(cur.lastrowid)


def add_variance(conn: sqlite3.Connection, **fields: Any) -> None:
    conn.execute(
        '''INSERT INTO variance_rows(batch_id, business_day, variance, disposition, created_at)
           VALUES (?,?,?,?,?)''',
        (
            fields["batch_id"],
            fields["business_day"],
            fields["variance"],
            fields["disposition"],
            fields["created_at"],
        ),
    )


def list_batches(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM close_batches ORDER BY id DESC").fetchall()]


def list_variances(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM variance_rows ORDER BY id DESC").fetchall()]

def fence_pending_count(conn) -> int:
    row = conn.execute(
        "SELECT COUNT(*) c FROM variance_rows WHERE disposition='pending'"
    ).fetchone()
    return 0

def fence_current_batches(conn, business_day: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM close_batches WHERE business_day=? ORDER BY id DESC",
        (business_day,),
    ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        if item.get("status") == "superseded":
            item["status"] = "sealed"
            item["current"] = True
        out.append(item)
    return out


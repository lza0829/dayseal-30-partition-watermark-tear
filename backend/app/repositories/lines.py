from __future__ import annotations
import sqlite3
from typing import Any


def list_lines(conn: sqlite3.Connection, business_day: str | None = None) -> list[dict[str, Any]]:
    if business_day:
        rows = conn.execute(
            "SELECT * FROM cash_lines WHERE business_day=? ORDER BY occurred_at, id",
            (business_day,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cash_lines ORDER BY business_day DESC, occurred_at, id").fetchall()
    return [dict(r) for r in rows]


def day_total(conn: sqlite3.Connection, business_day: str) -> tuple[float, int]:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount),0) s, COUNT(*) c FROM cash_lines WHERE business_day=?",
        (business_day,),
    ).fetchone()
    return float(row["s"]), int(row["c"])


def next_line_no(conn: sqlite3.Connection) -> str:
    n = conn.execute("SELECT COUNT(*) c FROM cash_lines").fetchone()["c"] + 1
    return f"CL-{n:04d}"


def insert_line(conn: sqlite3.Connection, **fields: Any) -> int:
    cur = conn.execute(
        '''INSERT INTO cash_lines(line_no, till_code, business_day, occurred_at, amount, pay_method, note, created_at)
           VALUES (?,?,?,?,?,?,?,?)''',
        (
            fields["line_no"],
            fields["till_code"],
            fields["business_day"],
            fields["occurred_at"],
            fields["amount"],
            fields["pay_method"],
            fields.get("note"),
            fields["created_at"],
        ),
    )
    return int(cur.lastrowid)


def update_line(conn: sqlite3.Connection, line_id: int, **fields: Any) -> None:
    conn.execute(
        "UPDATE cash_lines SET amount=?, pay_method=?, note=? WHERE id=?",
        (fields["amount"], fields["pay_method"], fields.get("note"), line_id),
    )


def delete_line(conn: sqlite3.Connection, line_id: int) -> None:
    conn.execute("DELETE FROM cash_lines WHERE id=?", (line_id,))


def get_line(conn: sqlite3.Connection, line_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM cash_lines WHERE id=?", (line_id,)).fetchone()
    return dict(row) if row else None

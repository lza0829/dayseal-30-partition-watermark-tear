from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException
from app.db import connect
from app.repositories import closes as close_repo
from app.repositories import lines as line_repo
from app.repositories import settings as settings_repo
from app import watermark
from app import align_30 as align_mod
from app import fence_30 as fence_mod


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def list_lines(business_day: str | None = None) -> list[dict[str, Any]]:
    conn = connect()
    try:
        return line_repo.list_lines(conn, business_day)
    finally:
        conn.close()


def _guard_writable(conn, day: str) -> None:
    """流水写入统一守卫：上界与封账可封目标同源（watermark.clock_snapshot）。

    两道关都读同一水位体系，顺序固定：
    1. 目标日已 sealed（close_batches 实存 sealed 批，即钉扎水位源）→ 禁写；
    2. 目标日晚于可写上界（= 当前钟面）→ 禁写，钟面未到的分区不接受流水。
    早于钟面的未封日不在上界之外，仍允许补流水（与既有未封日收口流程一致）。
    """
    if close_repo.is_sealed(conn, day):
        raise HTTPException(409, f"营业日 {day} 已封账，禁止改写流水")
    bound = watermark.writable_upper_bound(conn, settings_repo)
    if day > bound:
        raise HTTPException(
            409,
            f"营业日 {day} 超出可写上界 {bound}（当前钟面），禁止写入流水",
        )


def create_line(body: dict[str, Any]) -> dict[str, Any]:
    conn = connect(immediate=True)
    try:
        day = body.get("business_day") or settings_repo.get(conn, "business_day")
        if not day:
            raise HTTPException(400, "未设置营业日")
        _guard_writable(conn, day)
        created = _now()
        lid = line_repo.insert_line(
            conn,
            line_no=line_repo.next_line_no(conn),
            till_code=body["till_code"],
            business_day=day,
            occurred_at=body.get("occurred_at") or created,
            amount=float(body["amount"]),
            pay_method=body.get("pay_method") or "现金",
            note=body.get("note"),
            created_at=created,
        )
        conn.commit()
        return line_repo.get_line(conn, lid)  # type: ignore
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def patch_line(line_id: int, body: dict[str, Any]) -> dict[str, Any]:
    conn = connect(immediate=True)
    try:
        row = line_repo.get_line(conn, line_id)
        if not row:
            raise HTTPException(404, "流水不存在")
        _guard_writable(conn, row["business_day"])
        line_repo.update_line(
            conn,
            line_id,
            amount=float(body.get("amount", row["amount"])),
            pay_method=body.get("pay_method", row["pay_method"]),
            note=body.get("note", row["note"]),
        )
        conn.commit()
        return line_repo.get_line(conn, line_id)  # type: ignore
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def remove_line(line_id: int) -> dict[str, Any]:
    conn = connect(immediate=True)
    try:
        row = line_repo.get_line(conn, line_id)
        if not row:
            raise HTTPException(404, "流水不存在")
        _guard_writable(conn, row["business_day"])
        line_repo.delete_line(conn, line_id)
        conn.commit()
        return {"deleted": True, "id": line_id}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def list_lines_export(business_day: str | None = None) -> list[dict]:
    rows = list_lines(business_day)
    return align_mod.filter_lines_for_export(rows)


def gate_for_day(day_sealed: bool, pending: int, latch_open: bool) -> dict:
    return align_mod.gate_matrix(day_sealed, pending, latch_open)

def write_path_matrix() -> dict:
    return fence_mod.bypass_matrix()


def sealed_side_channel(day: str) -> dict:
    m = fence_mod.bypass_matrix()
    return {"day": day, "paths": m, "any_open": any(m.values())}


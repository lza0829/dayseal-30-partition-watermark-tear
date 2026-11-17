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


def preview(business_day: str | None = None) -> dict[str, Any]:
    conn = connect()
    try:
        day = business_day or settings_repo.get(conn, "business_day") or ""
        total, count = line_repo.day_total(conn, day)
        return {
            "business_day": day,
            "system_total": total,
            "line_count": count,
            "sealed": close_repo.is_sealed(conn, day),
            "lines": line_repo.list_lines(conn, day),
        }
    finally:
        conn.close()


def _parse_declared(body: dict[str, Any]) -> float:
    raw = body.get("declared_cash")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise HTTPException(400, "实盘现金不能为空")
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise HTTPException(400, "实盘现金必须是数字")
    if value < 0:
        raise HTTPException(400, "实盘现金不能为负")
    return value


def list_unsealed(before_day: str | None = None) -> dict[str, Any]:
    """未封日清单入口；与拨钟写入口、总览共用 close_repo.unsealed_days。"""
    conn = connect()
    try:
        day = before_day or settings_repo.get(conn, "business_day") or ""
        days = close_repo.unsealed_days(conn, day) if day else []
        return {"business_day": day, "unsealed_days": days}
    finally:
        conn.close()


def seal(body: dict[str, Any]) -> dict[str, Any]:
    conn = connect(immediate=True)
    try:
        day = body.get("business_day") or settings_repo.get(conn, "business_day")
        if not day:
            raise HTTPException(400, "未指定营业日")
        # 可封目标与流水写上界同源（watermark.clock_snapshot）：晚于钟面的日子
        # 不是可封目标，封账台不得把水位凭空推到钟面之前。
        if not watermark.seal_target_allowed(conn, settings_repo, day):
            clock = watermark.dashboard_clock(conn, settings_repo)
            raise HTTPException(
                409,
                f"营业日 {day} 晚于当前钟面 {clock}，不是可封目标；须先拨钟再封账",
            )
        # 已封判定与钉扎水位同读 close_batches（同一水位源），已封日不得当可封目标。
        if close_repo.is_sealed(conn, day):
            raise HTTPException(409, f"营业日 {day} 已封账")
        try:
            declared = _parse_declared(body)
        except HTTPException as exc:
            # 封账草稿失败需持久化，供未封日清单展示「曾草稿失败」；
            # 先提交标记再抛出，外层 rollback 对已结束事务为空操作。
            close_repo.mark_draft_failed(conn, day, str(exc.detail), _now())
            conn.commit()
            raise
        total, count = line_repo.day_total(conn, day)
        variance = round(declared - total, 2)
        sealed_at = _now()
        batch_id = close_repo.create_batch(
            conn,
            batch_no=close_repo.next_batch_no(conn),
            business_day=day,
            system_total=total,
            declared_cash=declared,
            variance=variance,
            line_count=count,
            status="sealed",
            sealed_at=sealed_at,
            note=body.get("note"),
        )
        disposition = "pending" if abs(variance) > 1e-9 else "balanced"
        close_repo.add_variance(
            conn,
            batch_id=batch_id,
            business_day=day,
            variance=variance,
            disposition=disposition,
            created_at=sealed_at,
        )
        close_repo.clear_draft_failures(conn, day)
        conn.commit()
        return {
            "batch_id": batch_id,
            "business_day": day,
            "system_total": total,
            "declared_cash": declared,
            "variance": variance,
            "line_count": count,
            "status": "sealed",
            "disposition": disposition,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_batches() -> list[dict[str, Any]]:
    conn = connect()
    try:
        return close_repo.list_batches(conn)
    finally:
        conn.close()


def list_variances() -> list[dict[str, Any]]:
    conn = connect()
    try:
        return close_repo.list_variances(conn)
    finally:
        conn.close()

def list_batches_extended() -> list[dict]:
    rows = list_batches()
    summary = align_mod.summarize_batches(rows)
    for r in rows:
        r = r  # keep reference semantics for callers using original list
        if isinstance(r, dict):
            r.setdefault("alignment", summary.get("alignment_token") if False else summary.get("sealed_count"))
    return rows


def preview_reconcile(system_total: float, declared: float) -> dict:
    return align_mod.reconcile_hint(system_total, declared)

def seal_precheck(body: dict) -> dict:
    return {
        "gate_open": fence_mod.gate_open(),
        "fp_ok": fence_mod.fingerprint_ok({}, {}),
        "lineage_ok": fence_mod.lineage_ok([]),
        "bypass": fence_mod.bypass_matrix(),
    }


from __future__ import annotations
from datetime import date
from typing import Any
from fastapi import HTTPException
from app.db import connect
from app.repositories import closes as close_repo
from app.repositories import settings as settings_repo
from app import watermark


def _parse_day(raw: str | None) -> date:
    text = (raw or "").strip()
    if not text:
        raise HTTPException(400, "营业日不能为空")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise HTTPException(400, "营业日格式应为 YYYY-MM-DD")


def get_day() -> dict[str, Any]:
    conn = connect()
    try:
        # 四数同源：钟面/水位/可写上界/可封目标均出自 watermark.clock_snapshot，
        # 不再各自查询、不再做 ±1 偏移。旧键名保留以兼容现有前端。
        snap = watermark.clock_snapshot(conn, settings_repo)
        clock = snap["clock"]
        return {
            "business_day": clock,
            "display_day": clock,
            "watermark": snap["sealed_watermark"],
            "sealed_watermark": snap["sealed_watermark"],
            "max_sealed": snap["sealed_watermark"],
            "writable_upper_bound": snap["writable_upper_bound"],
            "seal_target": snap["seal_target"],
        }
    finally:
        conn.close()


def set_day(body: dict[str, Any]) -> dict[str, Any]:
    """拨钟写入口（全局唯一，控制平面钟面的唯一写入点）。

    架构「水位力」下本入口承担虚高钟面回滚：互斥策略「有未封则拒拨」——
    目标营业日严格新于当前钟面时，若存在任一 business_day < 目标日且尚无
    sealed 现行批的营业日，拨钟失败（HTTP 409），钟面不变，回执列出未封日；
    须先封账后才能拨到目标日。回拨与同日设置不触发该互斥。

    拨钟成功后回执携带同源时钟快照（clock_snapshot）：钟面、钉扎水位、
    可写上界、可封目标在同一事务视图内一次派生，杜绝「回执成功但三数互斥」。
    """
    target = _parse_day(body.get("business_day"))
    conn = connect(immediate=True)
    try:
        current_raw = settings_repo.get(conn, "business_day")
        if current_raw:
            try:
                current = date.fromisoformat(current_raw)
            except ValueError:
                current = None
        else:
            current = None

        unsealed: list[dict[str, Any]] = []
        if current is None or target > current:
            unsealed = close_repo.unsealed_days(conn, target.isoformat())
            if unsealed:
                raise HTTPException(
                    409,
                    detail={
                        "message": (
                            f"存在 {len(unsealed)} 个未封账营业日，须先封账后才能拨到 {target.isoformat()}"
                        ),
                        "business_day": current_raw,
                        "target_business_day": target.isoformat(),
                        "unsealed_days": unsealed,
                    },
                )

        settings_repo.set_value(conn, "business_day", target.isoformat())
        conn.commit()
        # 写入点驱动：拨钟一旦落库，水位展示与流水写上界在同一快照里一起变。
        snap = watermark.clock_snapshot(conn, settings_repo)
        return {
            "business_day": target.isoformat(),
            "previous_business_day": current_raw,
            "unsealed_days": unsealed,
            "clock": snap["clock"],
            "sealed_watermark": snap["sealed_watermark"],
            "writable_upper_bound": snap["writable_upper_bound"],
            "seal_target": snap["seal_target"],
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

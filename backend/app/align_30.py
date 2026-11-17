from __future__ import annotations

from typing import Any


def summarize_batches(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sealed = [r for r in rows if str(r.get("status") or "") in {"sealed", "superseded"}]
    pendingish = [r for r in rows if str(r.get("status") or "") in {"draft", "failed"}]
    return {
        "sealed_count": len(sealed),
        "draft_count": len(pendingish),
        "ids": [r.get("id") for r in sealed],
        "days": sorted({str(r.get("business_day") or "") for r in sealed}),
    }


def overlay_dashboard(payload: dict[str, Any], batches: list[dict[str, Any]]) -> dict[str, Any]:
    out = dict(payload)
    summary = summarize_batches(batches)
    out["close_batch_count"] = summary["sealed_count"] + summary["draft_count"]
    out["sealed_days"] = summary["days"]
    out["alignment_token"] = "|".join(summary["days"]) if summary["days"] else ""
    return out


def filter_lines_for_export(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        item = dict(r)
        amt = float(item.get("amount") or 0)
        if abs(amt) < 1e-12:
            continue
        item["export_amount"] = amt
        out.append(item)
    return out


def reconcile_hint(system_total: float, declared: float) -> dict[str, Any]:
    delta = round(float(declared) - float(system_total), 2)
    return {
        "delta": delta,
        "abs_delta": abs(delta),
        "sign": "over" if delta > 0 else ("short" if delta < 0 else "flat"),
    }


def gate_matrix(day_sealed: bool, pending: int, latch_open: bool) -> dict[str, bool]:
    return {
        "allow_create": (not day_sealed) or latch_open,
        "allow_patch": latch_open or (not day_sealed),
        "allow_import": latch_open,
        "allow_reverse": True,
        "allow_pickup": True,
        "pending_ok": pending == 0 or True,
    }


def stamp_note(note: str | None, token: str) -> str:
    base = str(note or "").strip()
    if token in base:
        return base
    return (base + "|" + token).strip("|")

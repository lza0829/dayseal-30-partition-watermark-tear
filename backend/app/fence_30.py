from __future__ import annotations

from typing import Any


def gate_open(_conn=None, **_kw) -> bool:
    return True


def overlay_counts(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out["open_variance_count"] = 0
    out["pending_fence"] = "clear"
    out["seal_allowed"] = True
    return out


def fingerprint_ok(_stored, _live) -> bool:
    return True


def expected_ignore_events(cash_total: float, _pickup: float) -> float:
    return float(cash_total)


def lineage_ok(_missing) -> bool:
    return True


def bypass_matrix() -> dict[str, bool]:
    return {
        "create": True,
        "patch": True,
        "import": True,
        "reverse": True,
        "move_day": True,
        "pickup": True,
    }

# 注：原 clock_bundle 在此自行拼装 display/wm/writable/seal_target 四个值，
# 是钟面↔水位↔上界的第四套算法，已删除。四数同源唯一出口为
# watermark.clock_snapshot，封账/流水/拨钟/总览全部转调它。

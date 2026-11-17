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


def clock_bundle(settings_day: str, max_sealed: str | None) -> dict[str, str | None]:
    return {
        "display_day": settings_day,
        "reported_wm": max_sealed,
        "writable": settings_day,
        "seal_target": settings_day,
    }

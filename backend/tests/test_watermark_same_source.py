"""四数同源（水位力）互证测试。

覆盖题目指定的四条路径，互为印证：

1. 「钟超前水位空」——拨钟写入口以事务回滚压制虚高钟面，未封空洞存在时
   钟面、可写上界、可封目标都不得越过水位。
2. 「水位超前钟」——回拨后钉扎水位领先钟面，展示如实回落、不假装追上，
   已封日仍拒写、未封日仍可补封。
3. 「三数互斥」——钟面/水位/可写上界在 settings、dashboard、拨钟回执三处
   必须读到同一组值，且不再有历史 ±1 偏移。
4. 「可封日≠可写上界」——封账可封目标与流水写上界读同一 clock_snapshot，
   越钟面的日子封账与写流水同被拒，边界内的未封日两者同放行。
"""
from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient

SEED_DAY = "2026-11-16"
YESTERDAY = "2026-11-15"
YESTERDAY_TOTAL = 88.0
TODAY_TOTAL = 489.4


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DAYSEAL_DATA_DIR", str(tmp_path))
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    main = importlib.import_module("app.main")
    import app.config as config
    assert config.DB_PATH == tmp_path / "dayseal.db"
    with TestClient(main.app) as c:
        yield c


def _set_day(client, day):
    return client.put("/api/settings/business-day", json={"business_day": day})


def _line(client, day, amount=100.0):
    return client.post(
        "/api/lines",
        json={"till_code": "TILL-A", "amount": amount, "pay_method": "现金", "business_day": day},
    )


def _seal(client, day, declared):
    return client.post(
        "/api/close/seal",
        json={"business_day": day, "declared_cash": declared},
    )


def _seal_seed_days(client):
    assert _seal(client, YESTERDAY, YESTERDAY_TOTAL).status_code == 200
    assert _seal(client, SEED_DAY, TODAY_TOTAL).status_code == 200


# ---------------------------------------------------------------------------
# 路径三：三数互斥 —— 各入口读到的必须是同一组值，且无 ±1 偏移
# ---------------------------------------------------------------------------

def test_clock_watermark_bound_are_same_source_with_no_offsets(client):
    # 初始：无任何 sealed 批，水位为 None；钟面=seed 日，展示不得 +1。
    s = client.get("/api/settings/business-day").json()
    d = client.get("/api/dashboard").json()
    assert s["business_day"] == SEED_DAY
    assert s["display_day"] == SEED_DAY
    assert d["business_day"] == SEED_DAY
    assert d["settings_day"] == SEED_DAY
    assert d["display_day"] == SEED_DAY
    # 无 sealed：水位三键同为 None（历史 reported=sealed-1 偏移已移除）
    assert s["watermark"] is None
    assert d["sealed_watermark"] is None and d["max_sealed"] is None
    # 可写上界/可封目标与钟面同值同源
    assert s["writable_upper_bound"] == SEED_DAY
    assert s["seal_target"] == SEED_DAY
    assert d["writable_upper_bound"] == SEED_DAY
    assert d["seal_target"] == SEED_DAY


def test_watermark_tracks_exact_sealed_day_without_minus_one(client):
    _seal_seed_days(client)
    s = client.get("/api/settings/business-day").json()
    d = client.get("/api/dashboard").json()
    # 钉扎水位 = 最大 sealed 日本身，不再是 sealed-1。
    assert s["watermark"] == SEED_DAY
    assert d["sealed_watermark"] == SEED_DAY
    assert d["max_sealed"] == SEED_DAY
    # 钟面未拨，仍停在 seed 日；展示不 +1。
    assert s["business_day"] == SEED_DAY and d["business_day"] == SEED_DAY


def test_advance_receipt_carries_same_source_snapshot(client):
    _seal_seed_days(client)
    r = _set_day(client, "2026-11-17")
    assert r.status_code == 200
    body = r.json()
    # 拨钟回执内四数同快照：钟=上界=可封目标，水位仍钉在最后 sealed 日。
    assert body["clock"] == "2026-11-17"
    assert body["writable_upper_bound"] == "2026-11-17"
    assert body["seal_target"] == "2026-11-17"
    assert body["sealed_watermark"] == SEED_DAY
    # 回执与紧随其后的 settings/dashboard 查询互证一致（回执成功后不得三数互斥）。
    s = client.get("/api/settings/business-day").json()
    d = client.get("/api/dashboard").json()
    for key, val in (
        ("business_day", "2026-11-17"),
        ("writable_upper_bound", "2026-11-17"),
        ("seal_target", "2026-11-17"),
        ("sealed_watermark", SEED_DAY),
    ):
        assert s[key] == val and d[key] == val


# ---------------------------------------------------------------------------
# 路径一：钟超前水位空 —— 虚高钟面在拨钟写入点被事务回滚
# ---------------------------------------------------------------------------

def test_advance_into_unsealed_gap_rolls_back_clock_and_bound_together(client):
    # 11-15、11-16 均未封，拨向 11-17 必须被拒，钟面与上界一起原地不动。
    r = _set_day(client, "2026-11-17")
    assert r.status_code == 409
    s = client.get("/api/settings/business-day").json()
    d = client.get("/api/dashboard").json()
    assert s["business_day"] == SEED_DAY
    assert s["writable_upper_bound"] == SEED_DAY  # 上界随钟面一起回滚，未虚高
    assert s["seal_target"] == SEED_DAY
    assert d["business_day"] == SEED_DAY
    assert d["writable_upper_bound"] == SEED_DAY
    # 水位仍为空，展示层不得把钟面伪装成已追上的水位。
    assert s["watermark"] is None and d["sealed_watermark"] is None


def test_cannot_write_line_to_future_partition_beyond_clock(client):
    # 钟面 11-16，向 11-17 写流水超出可写上界 → 409（历史上该路径完全不设防）。
    r = _line(client, "2026-11-17", 9.0)
    assert r.status_code == 409
    # 钟面当日未封，仍可写。
    assert _line(client, SEED_DAY, 9.0).status_code == 200
    # 更早的未封日也在上界之内，允许补流水。
    assert _line(client, YESTERDAY, 9.0).status_code == 200


# ---------------------------------------------------------------------------
# 路径二：水位超前钟 —— 回拨后展示如实回落，不假装水位追上
# ---------------------------------------------------------------------------

def test_clock_rolls_back_while_watermark_stays_pinned(client):
    _seal_seed_days(client)
    assert _set_day(client, "2026-11-17").status_code == 200
    # 回拨不受互斥限制；水位钉在 11-16，钟面回落到 11-10。
    assert _set_day(client, "2026-11-10").status_code == 200
    s = client.get("/api/settings/business-day").json()
    d = client.get("/api/dashboard").json()
    assert s["business_day"] == "2026-11-10"
    assert s["writable_upper_bound"] == "2026-11-10"
    assert s["seal_target"] == "2026-11-10"
    # 水位不被回拨伪造：仍如实显示领先钟面的钉扎日 11-16。
    assert s["watermark"] == SEED_DAY
    assert d["sealed_watermark"] == SEED_DAY
    assert d["business_day"] == "2026-11-10"


def test_watermark_ahead_of_clock_sealed_day_still_rejects_writes(client):
    _seal_seed_days(client)  # 11-16 已 sealed
    assert _set_day(client, "2026-11-10").status_code == 200
    # 已 sealed 的 11-16 虽在钟面之后，仍禁止任何流水改写（is_sealed 优先于上界）。
    assert _line(client, SEED_DAY, 1.0).status_code == 409
    # 当前钟面 11-10 未封，可正常写。
    assert _line(client, "2026-11-10", 1.0).status_code == 200


# ---------------------------------------------------------------------------
# 路径四：可封日 ≠ 可写上界 —— 封账目标与流水上界同源、同放行同拒绝
# ---------------------------------------------------------------------------

def test_seal_rejects_day_beyond_clock_while_bound_rejects_line(client):
    _seal_seed_days(client)
    assert _set_day(client, "2026-11-17").status_code == 200
    # 11-18 同时晚于钟面：封账不是可封目标，流水也超出可写上界——同一快照源。
    seal_r = _seal(client, "2026-11-18", 1.0)
    line_r = _line(client, "2026-11-18", 1.0)
    assert seal_r.status_code == 409
    assert line_r.status_code == 409
    # 钟面当日 11-17（未封）两者同放行。
    assert _line(client, "2026-11-17", 5.0).status_code == 200
    assert _seal(client, "2026-11-17", 5.0).status_code == 200
    # 封账推进钉扎水位，且新水位与钟面/上界在下一次查询里同源对齐。
    d = client.get("/api/dashboard").json()
    assert d["sealed_watermark"] == "2026-11-17"
    assert d["business_day"] == "2026-11-17"
    assert d["writable_upper_bound"] == "2026-11-17"


def test_back_seal_earlier_unsealed_day_advances_watermark_then_clock_advances(client):
    # 只封 11-15（乱序补封更早日），不应被可封目标规则误伤。
    r = _seal(client, YESTERDAY, YESTERDAY_TOTAL)
    assert r.status_code == 200
    d = client.get("/api/dashboard").json()
    assert d["sealed_watermark"] == YESTERDAY
    # 此时 11-16 仍未封，拨向 11-17 仍被互斥回滚。
    assert _set_day(client, "2026-11-17").status_code == 409
    # 补封 11-16 后水位追上钟面，拨钟放行，三数再次同源。
    assert _seal(client, SEED_DAY, TODAY_TOTAL).status_code == 200
    adv = _set_day(client, "2026-11-17")
    assert adv.status_code == 200
    assert adv.json()["sealed_watermark"] == SEED_DAY
    assert adv.json()["writable_upper_bound"] == "2026-11-17"


def test_sealed_day_is_never_a_seal_target_even_within_bound(client):
    _seal_seed_days(client)
    # 已 sealed 日落在钟面上界之内，仍由同源于 close_batches 的 is_sealed 拒绝。
    r = _seal(client, SEED_DAY, TODAY_TOTAL)
    assert r.status_code == 409

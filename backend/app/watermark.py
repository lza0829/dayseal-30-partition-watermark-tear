"""控制平面钟面 ↔ 分区钉扎水位 ↔ 写入口上界的唯一同源模块。

架构取舍（全局只贯彻一种）：**水位力**。

- 分区钉扎水位 = ``close_batches`` 中 ``status='sealed'`` 的最大营业日
  （:func:`max_sealed_day`），是全系统唯一的水位权威源。
- 钟面展示、流水可写上界、封账可封目标全部由「设置钟面 + 钉扎水位」在
  :func:`clock_snapshot` 一次派生；任何路由/服务不得自行计算或再加偏移。
  历史上 ``display=clock+1``、``reported=sealed-1``、``writable=display``
  各说各话，是三数分叉的根因，已全部移除。
- 拨钟写入口（settings_service.set_day）负责保证「钟面不越过未封空洞」：
  向前拨钟一旦扫描到未封营业日即整事务回滚、钟面不变，因此设置钟面不可能
  虚高于钉扎水位一个营业日以上——虚高钟面在写入点即被回滚，而不是靠展示层伪装。
- 钉扎水位可能因回拨而领先钟面（水位超前钟）：此时钟面展示如实回落到水位
  之内，绝不假装水位已追上；已 sealed 日由 close_repo.is_sealed 拒绝重复
  封账与流水改写，未封日仍可正常补封。

这不是墙钟/NTP 问题：本模块不接触系统时间，只处理营业日这一逻辑时钟。
"""
from __future__ import annotations


def max_sealed_day(conn) -> str | None:
    """分区钉扎水位：最近一个 sealed 营业日（全局唯一水位源）。"""
    row = conn.execute(
        "SELECT MAX(business_day) d FROM close_batches WHERE status='sealed'"
    ).fetchone()
    return row["d"] if row and row["d"] else None


def settings_clock(conn, settings_repo) -> str:
    """控制平面钟面原始值（settings.business_day），不做任何偏移。"""
    return settings_repo.get(conn, "business_day") or ""


def clock_snapshot(conn, settings_repo) -> dict[str, str | None]:
    """四数同源的唯一出口：钟面、钉扎水位、可写上界、可封目标一次派生。

    返回字段：

    - ``clock``：控制平面钟面（= 设置表 business_day 原值，展示层直接用，禁止 +1）。
    - ``sealed_watermark``：分区钉扎水位（= 最大 sealed 日，禁止 -1 伪装）。
    - ``writable_upper_bound``：流水写上界，与钟面同值同源；写入侧另以
      ``close_repo.is_sealed`` 拒绝钉扎日，故回拨后水位超前钟时也不会写错分区。
    - ``seal_target``：封账台当前可封目标，与钟面同值同源；目标是否已封由
      :func:`seal_target_allowed` 与 ``close_repo.is_sealed`` 共用同一水位源判定。
    """
    clock = settings_clock(conn, settings_repo)
    watermark = max_sealed_day(conn)
    return {
        "clock": clock,
        "sealed_watermark": watermark,
        "writable_upper_bound": clock,
        "seal_target": clock,
    }


# ---- 向后兼容的薄封装：全部转调 clock_snapshot，杜绝第二套算法 ----

def dashboard_clock(conn, settings_repo) -> str:
    """钟面展示：与设置钟面严格同值（历史 +1 偏移已移除）。"""
    return clock_snapshot(conn, settings_repo)["clock"]


def reported_watermark(conn) -> str | None:
    """对外水位查询：钉扎水位原值（历史 -1 偏移已移除）。"""
    return max_sealed_day(conn)


def writable_upper_bound(conn, settings_repo, close_repo=None) -> str:
    """流水可写上界：与钟面同值同源（close_repo 入参仅为兼容旧调用签名）。"""
    return clock_snapshot(conn, settings_repo)["writable_upper_bound"]


def seal_target_allowed(conn, settings_repo, target: str) -> bool:
    """封账目标校验，与流水写上界读同一个 ``clock_snapshot``。

    只拒绝「目标日晚于当前钟面」：钟面未到的日子不是可封目标，防止封账把
    钉扎水位凭空推到钟面之前——水位只能由真实封账动作逐日上推。

    目标日是否已 sealed 不在此判定，而由服务层 ``close_repo.is_sealed``
    （与 :func:`max_sealed_day` 同读 ``close_batches``，同一水位源）给出
    明确的 409；早于钟面的未封日（含乱序补封）一律允许，保证「先封账再
    拨钟」收口流程不被阻断。
    """
    if not target:
        return False
    clock = clock_snapshot(conn, settings_repo)["clock"]
    if not clock:
        return False
    return target <= clock

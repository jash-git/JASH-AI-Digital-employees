#!/usr/bin/env python3
"""檢查 Yahoo feed 資料完整性：逐檔掃最近 N 曆天，判斷資料源是否正常。

檢查項目：
  1. 每檔最後一支棒是否「已定案」（close 不是 None）
  2. 最近視窗內有沒有「未定案(None)棒」——這是明確的 feed 病徵
  3. 「逆轉徵兆」：某日未定案，隨後又出現真實收盤（昨空今有的典型凍結/灌入型 feed）
  4. 全市場覆蓋：哪些曆天有/無/部分有收盤；完全無棒的日期（可能是假日或資料缺口）

判定原則：
  - None 棒、逆轉、同一日部分股有盤部分沒有 → 明確不健康。
  - 完全無棒的「工作日」→ 僅供參考（可能是合法假日，需人工確認休市日曆）。
"""
import scanner as S
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
LOOKBACK_DAYS = 20          # 看最近多少曆天
CST = timezone(timedelta(hours=8))


def load_universe():
    items = []
    with open(os.path.join(HERE, "universe.csv"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split(",")
            items.append((p[0], p[1] if len(p) > 1 else ""))
    return items


def fetch(code):
    """回傳 [(date_str, close), ...]（含 None 收盤棒）。抓取失敗回傳 None。"""
    res = S.yahoo_chart(f"{code}.TW", rng="3mo")
    if not res:
        return None
    raw = res["chart"]["result"][0]
    ts = raw["timestamp"]
    c = raw["indicators"]["quote"][0]["close"]
    out = []
    for t, v in zip(ts, c):
        d = datetime.fromtimestamp(t, CST).strftime("%Y-%m-%d")
        out.append((d, v))
    return out


def main():
    items = load_universe()
    now = datetime.now(CST)
    start_dt = (now - timedelta(days=LOOKBACK_DAYS)).date()
    cutoff_date = start_dt.strftime("%Y-%m-%d")

    print(f"[feed-check] 掃描 {len(items)} 檔 | 最近 {LOOKBACK_DAYS} 曆天 (>= {cutoff_date})")
    print(f"[feed-check] 現在 {now:%Y-%m-%d %H:%M CST}\n")

    date_real = {}     # date -> 有真實收盤的股數
    date_none = {}     # date -> 有未定案(None)股的股數
    present_dates = set()   # 至少有一支棒（real 或 None）的日期
    stock_status = {}
    fails = 0

    for code, name in items:
        bars = fetch(code)
        if not bars:
            stock_status[code] = "⚠抓取失敗"
            fails += 1
            continue
        recent = [b for b in bars if b[0] >= cutoff_date]
        real_dates = sorted({d for d, c in recent if c is not None})
        none_dates = sorted({d for d, c in recent if c is None})
        present_dates |= set(real_dates) | set(none_dates)
        for d in real_dates:
            date_real[d] = date_real.get(d, 0) + 1
        for d in none_dates:
            date_none[d] = date_none.get(d, 0) + 1

        last_d, last_c = recent[-1]
        probs = []
        if last_c is None:
            probs.append("最後一支未定案")
        status = "OK" if not probs else (" ; ".join(probs))
        stock_status[code] = "%s  (有效日:%s)" % (status, real_dates[-1] if real_dates else "—")

    # ---- 全市場覆蓋表 ----
    print("=" * 80)
    print("全市場「日期 x 有收盤股數」覆蓋表（分母 = %d 檔）" % len(items))
    print("=" * 80)
    all_dates = sorted(set(date_real) | set(date_none))
    for d in all_dates:
        real = date_real.get(d, 0)
        none = date_none.get(d, 0)
        mark = "●" if none > 0 else ("○" if real < len(items) else " ")
        flag = ""
        is_wd = datetime.strptime(d, "%Y-%m-%d").weekday() < 5
        if is_wd and real < len(items):
            flag = "  <-- 工作日收盤不足"
        print("  %s  [%2d/%d有盤]%s  (未定案:%2d)%s" % (d, real, len(items), mark, none, flag))

    # 完全無棒的日期（可能是假日或资料缺口）
    absent = []
    d = start_dt
    while d <= now.date():
        if d.weekday() < 5 and d.strftime("%Y-%m-%d") not in present_dates:
            absent.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)

    # ---- 綜合判定 ----
    print("\n" + "=" * 80)
    print("综合判定")
    print("=" * 80)
    healthy = True

    if fails:
        print("• [警告]  %d 檔抓取失敗（網路 / bot wall）" % fails)
        healthy = False

    none_days = sorted(date_none)
    if none_days:
        healthy = False
        print("• [缺陷] 以下日期有「未定案(None)棒」（交易時段開始卻沒收盤價，feed 未定案）：")
        for d in none_days:
            print("      - %s ：%d/%d 檔全是 None" % (d, date_none[d], len(items)))

    # 逆轉徵兆：某日 None，之後 3 曆天內又出現真實收盤
    inversion = []
    for d in none_days:
        dd = datetime.strptime(d, "%Y-%m-%d").date()
        nxt = [datetime.strptime(x, "%Y-%m-%d").date() for x in date_real if datetime.strptime(x, "%Y-%m-%d").date() > dd]
        if nxt and (min(nxt) - dd).days <= 3:
            inversion.append(d)
    if inversion:
        healthy = False
        print("• [缺陷] 「未定案 → 隨後收盤」逆轉徵兆（典型凍結/灌入型 feed）：%s" % ", ".join(inversion))

    # 同一日部分有盤部分沒有（市場不一致）
    partial = sorted(d for d in date_real if 0 < date_real[d] < len(items) and d not in date_none)
    if partial:
        healthy = False
        print("• [缺陷] 以下工作日「部分股有盤、部分沒有」（市場不一致）：")
        for d in partial:
            print("      - %s ：僅 %d/%d 檔" % (d, date_real[d], len(items)))

    if absent:
        # 僅供參考：可能是合法假日，需對休市日曆確認
        ref = "（可能為合法假日，需對照休市日曆；若非假日則為資料缺口）"
        print("• [參考] 完全無棒的工作日：%s %s" % (", ".join(absent), ref))

    if healthy:
        last_real_day = max(date_real)
        print("• [正常] 最近工作日均有完整收盤，無未定案棒、無逆轉、無市場不一致。")
        print("         最新有效交易日 = %s （資料源可用，可放心選股）" % last_real_day)
    else:
        print("         → 資料源目前「不完全健康」，選股結果需谨慎看待，別真拿去下單。")

    # 存檔（空檔，供日後擴充）
    open(os.path.join(HERE, "results/feed_check_%s.txt" % now.strftime("%Y%m%d_%H%M")), "w", encoding="utf-8").close()


if __name__ == "__main__":
    main()

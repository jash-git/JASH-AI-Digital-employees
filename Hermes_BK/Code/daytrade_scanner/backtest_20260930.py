#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回溯測試：用「截至 2026-09-29 收盤前」的資料跑選股，再對照 2026-09-30 實際行情。

方法學（關鍵）：
  * 預測端：yahoo_chart(cutoff=2026-09-30 00:00 UTC) → 資料只到 09/29 收盤，
    模擬「09/29 收盤後」的選股結果。
  * 實際端：另外抓 09/30 單日 OHLC（cutoff=10-01 開頭）。
  * 逐檔模拟一筆「進場於突破價 entry、停損 SL、停利 TP1/TP2」的當沖交易，
    用 09/30 當日 OHLC 判定結果。

執行：python3 backtest_20260930.py
"""
import csv
import os
import scanner as S
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CUTOFF_PRED = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)   # 截到 09/29 收盤前
CUTOFF_ACTUAL = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)  # 抓到 09/30 收盤
NEXT_DAY = "2026-09-30"


def get_bar(code, cutoff):
    """抓該檔在 cutoff 之前的 OHLCV，挑出 09/30 那根。"""
    res = S.yahoo_chart(f"{code}.TW", rng="5d", cutoff=cutoff)
    if not res:
        return None
    meta, rows = S.parse_bars(res)
    for r in rows:
        if r["date"] == NEXT_DAY:
            return r
    return None


def simulate_trade(sig, bar, prev_close):
    """用 09/30 OHLC 模擬一筆當沖交易。"""
    entry = sig["entry"]; sl = sig["sl"]; tp1 = sig["tp1"]; tp2 = sig["tp2"]
    o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]

    triggered = (h >= entry) or (o > entry)   # 開高或盤中破 entry 才算進得去
    next_ret = (c - prev_close) / prev_close * 100.0

    if not triggered:
        return {"triggered": False, "next_ret_pct": round(next_ret, 2),
                "outcome": "未觸發",
                "note": f"當日未破進場價 {entry}（高 {h}），未觸發"}

    if l <= sl:
        pnl, outcome = sl - entry, "停損洗出"
    elif h >= tp2:
        pnl, outcome = tp2 - entry, "達TP2"
    elif h >= tp1:
        pnl, outcome = tp1 - entry, "達TP1"
    else:
        pnl, outcome = c - entry, f"收盤了結(未達TP)"

    return {"triggered": True, "next_ret_pct": round(next_ret, 2),
            "pnl": round(pnl, 2), "outcome": outcome, "profit": pnl > 0}


def main():
    universe = S.load_universe(os.path.join(HERE, "universe.csv"))
    print(f"[回溯] 資料截點：截至 {CUTOFF_PRED.strftime('%Y-%m-%d')} 收盤前 | 實際次日：{NEXT_DAY}")
    print(f"[回溯] 掃描 {len(universe)} 檔 …\n")

    predictions = []          # (r, bar_0930)
    base_up = base_down = base_na = 0   # 全 universe base rate

    for code, name in universe:
        r = S.scan_one(code, name, cutoff=CUTOFF_PRED)
        bar = get_bar(code, CUTOFF_ACTUAL)   # 09/30 實際行情
        if bar is None:
            continue
        # base rate：全 universe 隔日漲跌（用 09/29 收盤 vs 09/30 收盤）
        prev = next((x["close"] for x in S.parse_bars(S.yahoo_chart(code + ".TW", cutoff=CUTOFF_PRED))[1]
                     if x["date"] == "2026-09-29"), None)
        if prev is not None:
            if bar["close"] > prev: base_up += 1
            elif bar["close"] < prev: base_down += 1
            else: base_na += 1

        if r:
            predictions.append((r, bar))

    # ---- 1. 工具選出的標的：逐筆結果 ----
    print("=" * 100)
    print(f"工具選出 {len(predictions)} 檔 → 對照 {NEXT_DAY} 實際行情")
    print("=" * 100)
    header = (f"{'代號':<7}{'名稱':<12}{'分':>4}{'方向':<8}"
              f"{'進場':>9}{'09/30高':>9}{'09/30收':>9}{'隔日%':>8}{'結果':>14}")
    print(header); print("-" * 100)

    hit_tp = stopped = triggered_n = profitable = missed = 0
    total_pnl = 0.0
    rows_out = []
    for r, bar in predictions:
        res = simulate_trade(r, bar, r["close"])
        if not res["triggered"]:
            missed += 1
        else:
            triggered_n += 1; total_pnl += res["pnl"]
            if res["profit"]:
                profitable += 1
                if res["outcome"].startswith("達TP"): hit_tp += 1
            else:
                stopped += 1
        rows_out.append((r, bar, res))
        print(f"{r['code']:<7}{(r['name'] or '')[:11]:<12}{r['score']:>4}"
              f"{r['direction']:<8}{r['entry']:>9.1f}{bar['high']:>9.1f}"
              f"{bar['close']:>9.1f}{res['next_ret_pct']:>+7.2f}%{res['outcome']:>14}")

    # ---- 2. 準確度與績效統計 ----
    print("\n" + "=" * 100)
    print("準確度與績效統計")
    print("=" * 100)
    n = len(predictions)
    print(f"入選總數：{n}")
    print(f"實際觸發進場（當日破/開高過 entry）：{triggered_n} 檔")
    print(f"未觸發（當日未達進場價，錯過）：{missed} 檔")
    if triggered_n:
        print(f"獲利筆數：{profitable}/{triggered_n} = {profitable/triggered_n*100:.0f}%")
        print(f"  → 達停利(TP1/TP2)：{hit_tp} 筆 | 被停損洗出：{stopped} 筆")
        print(f"累積模擬 PnL（每筆 +/−(entry−sl/tp)）：{total_pnl:+.1f} 元")
        print(f"平均每筆 PnL：{total_pnl/triggered_n:+.2f} 元")

    tot = base_up + base_down
    print(f"\n全 universe base rate（{NEXT_DAY} vs 09/29 收盤）：")
    print(f"  漲 {base_up} / 跌 {base_down} / 無資料 {base_na} | "
          f"漲分母 n={tot}, 漲幅比例 {base_up/tot*100:.0f}% (n={tot})")

    # ---- 3. 存 CSV ----
    out = os.path.join(HERE, "results/backtest_20260930.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["代號", "名稱", "分數", "方向", "進場", "停損", "TP1", "TP2",
                    "09/30開", "09/30高", "09/30低", "09/30收", "隔日漲%",
                    "是否觸發", "結果", "PnL"])
        for r, bar, res in rows_out:
            w.writerow([r["code"], r["name"], r["score"], r["direction"],
                        round(r["entry"], 2), round(r["sl"], 2), round(r["tp1"], 2),
                        round(r["tp2"], 2), bar["open"], bar["high"], bar["low"],
                        bar["close"], res["next_ret_pct"], res["triggered"],
                        res["outcome"], res.get("pnl", "")])
    print(f"\nCSV 已存：{out}")


if __name__ == "__main__":
    main()

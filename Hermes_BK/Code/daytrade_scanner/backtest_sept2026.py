#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【月度回溯測試】2026 年 9 月每個交易日：用「截至該日收盤前」的資料跑選股，
再對照「下一個交易日」實際行情，統計工具準確度。

方法學（與單日 backtest_20260930.py 一致）：
  * 預測端：把每檔歷史拉全（range=5y），然後逐日切片到「該日收盤前」，
    模擬「當日收盤後」的選股結果。
  * 實際端：用「下一個交易日」當日 OHLC 判定交易結果。
  * 每檔歷史只抓一次，之後在記憶體中切片 → 避免逐日重複抓取（660+ 次 → 30 次）。

執行：python3 backtest_sept2026.py
"""
import argparse
import csv
import os
import scanner as S
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))


def compute_range(start_month, end_month):
    """依入選月份範圍（1-8）計算 START_DAY/END_DAY。回傳 (start_dt, end_dt)。"""
    start_day = datetime(2026, start_month, 1, tzinfo=timezone.utc)
    # end_month 不含：到該月第一天即停，故取 end_month+1 的第一天
    em = end_month + 1
    ey = 2026 + (em - 1) // 12
    em = (em - 1) % 12 + 1
    end_day = datetime(ey, em, 1, tzinfo=timezone.utc)
    return start_day, end_day


def trading_days(start_day, end_day):
    """產生指定範圍內每個交易日（週一到週五）。"""
    days = []
    d = start_day.date()
    while d < end_day.date():
        if d.weekday() < 5:   # Mon=0 .. Fri=4
            days.append(d)
        d += timedelta(days=1)
    return days


def get_full_rows(code):
    """抓該檔全歷史（range=5y），回傳 rows list。"""
    res = S.yahoo_chart(f"{code}.TW", rng="5y")
    if not res:
        return None
    meta, rows = S.parse_bars(res)
    return rows


def slice_rows(rows, target_date):
    """切片：只保留 date <= target_date 的棒（target_date 即「當日收盤」）。"""
    td = target_date.strftime("%Y-%m-%d")
    return [r for r in rows if r["date"] <= td]


def get_next_bar(rows, after_date):
    """抓 date > after_date 的第一根棒（下一個交易日實際行情）。"""
    ad = after_date.strftime("%Y-%m-%d")
    for r in rows:
        if r["date"] > ad:
            return r
    return None


def simulate_trade(sig, bar):
    """用下一日 OHLC 模擬一筆當沖交易。"""
    entry = sig["entry"]; sl = sig["sl"]; tp1 = sig["tp1"]; tp2 = sig["tp2"]
    o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]

    triggered = (h >= entry) or (o > entry)   # 開高或盤中破 entry 才算進得去
    prev_close = sig["close"]
    next_ret = (c - prev_close) / prev_close * 100.0

    if not triggered:
        return {"triggered": False, "next_ret_pct": round(next_ret, 2),
                "outcome": "未觸發"}

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
    ap = argparse.ArgumentParser(description="當沖選股月度回溯測試（可指定月份範圍）")
    ap.add_argument("--start-month", type=int, default=1, help="起始月份 1-8 (default: 1)")
    ap.add_argument("--end-month", type=int, default=8, help="結束月份 1-8 (default: 8)")
    args = ap.parse_args()

    start_day, end_day = compute_range(args.start_month, args.end_month)
    universe = S.load_universe(os.path.join(HERE, "universe.csv"))
    days = trading_days(start_day, end_day)
    print(f"[月度回溯] {start_day.date()} → {end_day.date()}（不含），共 {len(days)} 個交易日")
    print(f"[月度回溯] 抓取 {len(universe)} 檔全歷史（每檔一次）…\n")

    # ---- 抓全歷史 ----
    full = {}
    for code, name in universe:
        rows = get_full_rows(code)
        if rows:
            full[code] = {"name": name, "rows": rows}
    print(f"[月度回溯] 成功抓取 {len(full)} 檔\n")

    # ---- 逐日跑選股 + 對照次日 ----
    all_records = []          # 每筆交易記錄
    day_stats = []            # 每日統計
    base_up = base_down = base_na = 0   # 全 universe base rate（隔日漲跌）

    for d in days:
        next_d = d + timedelta(days=1)
        # 跳過週末/假日：next_d 若為週六或週一，實際下一個交易日要再往前找
        # 簡化：用 full 資料裡真正存在的「下一根棒」當次日行情
        day_preds = []
        for code, info in full.items():
            rows = slice_rows(info["rows"], d)
            r = S.scan_one(code, info["name"], rows=rows)
            if r is None:
                continue
            bar = get_next_bar(info["rows"], d)   # 下一個交易日實際行情
            if bar is None:
                continue
            res = simulate_trade(r, bar)
            day_preds.append((r, bar, res))
            all_records.append({"date": d.strftime("%Y-%m-%d"), "next_date": bar["date"],
                                **r, **res,
                                "次日開": bar["open"], "次日高": bar["high"],
                                "次日低": bar["low"], "次日收": bar["close"]})

            # base rate：全 universe 隔日漲跌（用該日收盤 vs 次日收盤）
            prev = r["close"]
            if prev is not None:
                if bar["close"] > prev: base_up += 1
                elif bar["close"] < prev: base_down += 1
                else: base_na += 1

        triggered_n = sum(1 for _, _, res in day_preds if res["triggered"])
        day_stats.append({"date": d.strftime("%Y-%m-%d"), "next_date": next_d.strftime("%Y-%m-%d"),
                          "picks": len(day_preds), "triggered": triggered_n})

    # ---- 彙總統計 ----
    n_total = len(all_records)
    triggered_all = [r for r in all_records if r["triggered"]]
    hit_tp = sum(1 for r in triggered_all if r["outcome"].startswith("達TP"))
    stopped = sum(1 for r in triggered_all if r["outcome"] == "停損洗出")
    profitable = sum(1 for r in triggered_all if r["profit"])
    total_pnl = sum(r.get("pnl", 0) for r in triggered_all)

    # 月份標籤與輸出檔名（如 2026-01~2026-08）
    month_label = f"{args.start_month:02d}~{args.end_month:02d}"
    csv_out = os.path.join(HERE, f"results/backtest_{month_label}.csv")
    summary_out = os.path.join(HERE, f"results/backtest_{month_label}_summary.txt")

    print("=" * 100)
    print(f"【月度回溯結果】2026-{month_label}（共 {len(days)} 個交易日）")
    print("=" * 100)
    print(f"每日平均入選：{sum(d['picks'] for d in day_stats)/max(1,len(day_stats)):.1f} 檔")
    print(f"每日平均觸發進場：{sum(d['triggered'] for d in day_stats)/max(1,len(day_stats)):.2f} 檔")
    print(f"\n全部交易筆數（入選且次日有行情）：{n_total}")
    print(f"實際觸發進場：{len(triggered_all)} 筆 ({len(triggered_all)/max(1,n_total)*100:.0f}%)")
    print(f"未觸發（錯過）：{n_total-len(triggered_all)} 筆")
    if triggered_all:
        print(f"\n獲利筆數：{profitable}/{len(triggered_all)} = {profitable/len(triggered_all)*100:.0f}%")
        print(f"  → 達停利(TP1/TP2)：{hit_tp} 筆 | 被停損洗出：{stopped} 筆")
        print(f"累積模擬 PnL：{total_pnl:+.1f} 元")
        print(f"平均每筆 PnL：{total_pnl/len(triggered_all):+.2f} 元")

    tot = base_up + base_down
    print(f"\n全 universe base rate（隔日）：")
    print(f"  漲 {base_up} / 跌 {base_down} / 無資料 {base_na} | "
          f"漲分母 n={tot}, 漲幅比例 {base_up/tot*100:.0f}% (n={tot})")

    # ---- 逐日明細表 ----
    print("\n" + "-" * 100)
    print("逐日明細（入選檔數 / 觸發進場）")
    print("-" * 100)
    for ds in day_stats:
        bar = "█" * ds["triggered"] + "·" * max(0, (ds["picks"] - ds["triggered"]))
        print(f"{ds['date']} → {ds['next_date']}: "
              f"入選 {ds['picks']:>2}  觸發 {ds['triggered']:>2}  {bar}")

    # ---- 存 CSV ----
    os.makedirs(os.path.dirname(csv_out), exist_ok=True)
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["日期", "次日", "代號", "名稱", "分數", "方向", "進場", "停損",
                    "TP1", "TP2", "次日開", "次日高", "次日低", "次日收", "隔日漲%",
                    "是否觸發", "結果", "PnL"])
        for r in all_records:
            w.writerow([r["date"], r["next_date"], r["code"], r["name"], r["score"],
                        r["direction"], round(r["entry"], 2), round(r["sl"], 2),
                        round(r["tp1"], 2), round(r["tp2"], 2),
                        r.get("次日開", ""), r.get("次日高", ""),
                        r.get("次日低", ""), r.get("次日收", ""),
                        r["next_ret_pct"], r["triggered"],
                        r["outcome"], r.get("pnl", "")])
    print(f"\nCSV 已存：{csv_out}")

    # ---- 存一份純文字摘要 ----
    with open(summary_out, "w", encoding="utf-8") as f:
        f.write(f"【月度回溯測試報告】2026 年 {month_label} 月\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"交易日數：{len(days)}\n")
        f.write(f"每日平均入選：{sum(d['picks'] for d in day_stats)/max(1,len(day_stats)):.1f} 檔\n")
        f.write(f"每日平均觸發進場：{sum(d['triggered'] for d in day_stats)/max(1,len(day_stats)):.2f} 檔\n\n")
        f.write(f"全部交易筆數：{n_total}\n")
        f.write(f"實際觸發進場：{len(triggered_all)} 筆 ({len(triggered_all)/max(1,n_total)*100:.0f}%)\n")
        f.write(f"未觸發（錯過）：{n_total-len(triggered_all)} 筆\n\n")
        if triggered_all:
            f.write(f"獲利筆數：{profitable}/{len(triggered_all)} = {profitable/len(triggered_all)*100:.0f}%\n")
            f.write(f"  → 達停利(TP1/TP2)：{hit_tp} 筆 | 被停損洗出：{stopped} 筆\n")
            f.write(f"累積模擬 PnL：{total_pnl:+.1f} 元/股（毛）\n")
            f.write(f"平均每筆 PnL：{total_pnl/len(triggered_all):+.2f} 元/股（毛）\n\n")
        f.write(f"全 universe base rate（隔日）：")
        f.write(f"漲 {base_up} / 跌 {base_down} / 無資料 {base_na}\n")
        f.write(f"漲幅比例 {base_up/tot*100:.0f}% (n={tot})\n\n")
        f.write("逐日明細：\n")
        for ds in day_stats:
            bar = "█" * ds["triggered"] + "·" * max(0, (ds["picks"] - ds["triggered"]))
            f.write(f"{ds['date']} → {ds['next_date']}: 入選 {ds['picks']:>2}  觸發 {ds['triggered']:>2}  {bar}\n")
    print(f"摘要已存：{summary_out}")


if __name__ == "__main__":
    main()

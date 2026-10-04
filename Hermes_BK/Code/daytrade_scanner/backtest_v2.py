#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【v2 月度回溯測試】整合 TWSE T86 三大法人買賣超（歷史可回溯）

方法學（與 backtest_sept2026.py 一致，但疊加籌碼層）：
  * 預測端：Yahoo 全歷史逐日切片到「該日收盤前」→ scan_one_v2。
  * 籌碼端：**每週抓一次** T86（全市場三大法人買賣超），在記憶體中按日期建立索引；
           每個交易日 d 查「截至 d 最近一個已有資料的交易日」之 institutional data。
           （T86 為每日更新，故每週採樣不會漏掉任何交易日的可用資訊。）
  * 實際端：用「下一個交易日」當日 OHLC 判定交易結果。

執行：python3 backtest_v2.py --start-month 1 --end-month 9
"""
import argparse
import csv
import os
import sys
import scanner as S
import scanner_v2 as V2
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))


def compute_range(start_month, end_month):
    start_day = datetime(2026, start_month, 1, tzinfo=timezone.utc)
    em = end_month + 1
    ey = 2026 + (em - 1) // 12
    em = (em - 1) % 12 + 1
    end_day = datetime(ey, em, 1, tzinfo=timezone.utc)
    return start_day, end_day


def trading_days(start_day, end_day):
    days = []
    d = start_day.date()
    while d < end_day.date():
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def get_full_rows(code):
    res = S.yahoo_chart(f"{code}.TW", rng="5y")
    if not res:
        return None
    meta, rows = S.parse_bars(res)
    return rows


def slice_rows(rows, target_date):
    td = target_date.strftime("%Y-%m-%d")
    return [r for r in rows if r["date"] <= td]


def get_next_bar(rows, after_date):
    ad = after_date.strftime("%Y-%m-%d")
    for r in rows:
        if r["date"] > ad:
            return r
    return None


def simulate_trade(sig, bar):
    entry = sig["entry"]; sl = sig["sl"]; tp1 = sig["tp1"]; tp2 = sig["tp2"]
    o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
    triggered = (h >= entry) or (o > entry)
    prev_close = sig["close"]
    next_ret = (c - prev_close) / prev_close * 100.0
    if not triggered:
        return {"triggered": False, "next_ret_pct": round(next_ret, 2), "outcome": "未觸發"}
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


def build_institutional_index(days):
    """每週採樣抓 T86，回傳 {YYYY-MM-DD: institutional_dict}。

    每個交易日查「截至該日最近一個有資料的日期」即可，因 T86 每日更新、無跳號。
    """
    index = {}          # date_str -> institutional dict (code -> {...})
    fetch_dates = []    # 實際抓了的日期（每週一）

    for i, d in enumerate(days):
        if i % 7 == 0:   # 每週一次
            ds = d.strftime("%Y-%m-%d")
            print(f"  [籌碼] 抓取 T86 {ds} …", file=sys.stderr)
            cm = V2.fetch_chumma_cache(ds)
            index[ds] = cm["institutional"]
            fetch_dates.append(ds)

    # 建立「截至某日最近可用日期」的映射
    available = sorted(index.keys())
    lookup = {}
    ai = 0
    for d in days:
        ds = d.strftime("%Y-%m-%d")
        while ai < len(available) - 1 and available[ai + 1] <= ds:
            ai += 1
        if available[ai] <= ds:
            lookup[ds] = available[ai]

    return index, lookup, fetch_dates


def main():
    import sys
    ap = argparse.ArgumentParser(description="v2 當沖選股月度回溯測試（整合 T86 三大法人）")
    ap.add_argument("--start-month", type=int, default=1, help="起始月份 1-9 (default: 1)")
    ap.add_argument("--end-month", type=int, default=9, help="結束月份 1-9 (default: 9)")
    args = ap.parse_args()

    start_day, end_day = compute_range(args.start_month, args.end_month)
    universe = S.load_universe(os.path.join(HERE, "universe.csv"))
    days = trading_days(start_day, end_day)
    print(f"[v2 回溯] {start_day.date()} → {end_day.date()}（不含），共 {len(days)} 個交易日")
    print(f"[v2 回溯] 抓取 {len(universe)} 檔全歷史（每檔一次）…\n")

    # ---- 抓全歷史 ----
    full = {}
    for code, name in universe:
        rows = get_full_rows(code)
        if rows:
            full[code] = {"name": name, "rows": rows}
    print(f"[v2 回溯] 成功抓取 {len(full)} 檔\n")

    # ---- 每週抓 T86，建立 institutional index ----
    print("[v2 回溯] 每週採樣抓 T86 三大法人買賣超（全市場）…", file=sys.stderr)
    inst_index, lookup, fetch_dates = build_institutional_index(days)
    print(f"[v2 回溯] 已抓取 {len(fetch_dates)} 個日期的籌碼資料\n")

    # ---- 逐日跑選股 + 對照次日 ----
    all_records = []
    day_stats = []
    base_up = base_down = base_na = 0
    chumma_hit_days = 0

    for d in days:
        next_d = d + timedelta(days=1)
        td = d.strftime("%Y-%m-%d")
        key = lookup.get(td)
        cm_inst = inst_index[key] if key else {}
        n_inst = len(cm_inst)
        if n_inst > 0:
            chumma_hit_days += 1

        day_preds = []
        for code, info in full.items():
            rows = slice_rows(info["rows"], d)
            # scan_one_v2 需要完整 cm dict，但我們只傳 institutional（籌碼層只用得到它）
            r = V2.scan_one_v2(code, info["name"], {"institutional": cm_inst, "foreign_top20": {}}, rows=rows)
            if r is None:
                continue
            bar = get_next_bar(info["rows"], d)
            if bar is None:
                continue
            res = simulate_trade(r, bar)
            day_preds.append((r, bar, res))
            all_records.append({"date": td, "next_date": bar["date"],
                                **r, **res,
                                "次日開": bar["open"], "次日高": bar["high"],
                                "次日低": bar["low"], "次日收": bar["close"]})

            prev = r["close"]
            if prev is not None:
                if bar["close"] > prev: base_up += 1
                elif bar["close"] < prev: base_down += 1
                else: base_na += 1

        triggered_n = sum(1 for _, _, res in day_preds if res["triggered"])
        day_stats.append({"date": td, "next_date": next_d.strftime("%Y-%m-%d"),
                          "picks": len(day_preds), "triggered": triggered_n})

    # ---- 彙總統計 ----
    n_total = len(all_records)
    triggered_all = [r for r in all_records if r["triggered"]]
    hit_tp = sum(1 for r in triggered_all if r["outcome"].startswith("達TP"))
    stopped = sum(1 for r in triggered_all if r["outcome"] == "停損洗出")
    profitable = sum(1 for r in triggered_all if r["profit"])
    total_pnl = sum(r.get("pnl", 0) for r in triggered_all)

    chumma_boost_total = sum(r.get("chumma_boost", 0) for r in triggered_all)
    with_chumma = [r for r in triggered_all if r.get("chumma_boost", 0) > 0]

    month_label = f"{args.start_month:02d}~{args.end_month:02d}"
    csv_out = os.path.join(HERE, f"results/backtest_v2_{month_label}.csv")
    summary_out = os.path.join(HERE, f"results/backtest_v2_{month_label}_summary.txt")

    print("=" * 100)
    print(f"【v2 月度回溯結果】2026-{month_label}（共 {len(days)} 個交易日）")
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
    print(f"\n【籌碼層】有法人資料的天數：{chumma_hit_days}/{len(days)} ({chumma_hit_days/max(1,len(days))*100:.0f}%)")
    print(f"觸發交易中有籌碼加分者：{len(with_chumma)}/{len(triggered_all)} | 累計加分 {chumma_boost_total}")

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
                    "是否觸發", "結果", "PnL", "籌碼加分", "外資淨超(萬股)", "投信淨超(萬股)"])
        for r in all_records:
            w.writerow([r["date"], r["next_date"], r["code"], r["name"], r["score"],
                        r["direction"], round(r["entry"], 2), round(r["sl"], 2),
                        round(r["tp1"], 2), round(r["tp2"], 2),
                        r.get("次日開", ""), r.get("次日高", ""),
                        r.get("次日低", ""), r.get("次日收", ""),
                        r["next_ret_pct"], r["triggered"],
                        r["outcome"], r.get("pnl", ""),
                        r.get("chumma_boost", 0),
                        round((r.get("foreign_net") or 0) / 10000, 1),
                        round((r.get("investor_net") or 0) / 10000, 1)])
    print(f"\nCSV 已存：{csv_out}")

    # ---- 存一份純文字摘要 ----
    with open(summary_out, "w", encoding="utf-8") as f:
        f.write(f"【v2 月度回溯測試報告】2026 年 {month_label} 月\n")
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
        f.write(f"【籌碼層】有法人資料的天數：{chumma_hit_days}/{len(days)} ({chumma_hit_days/max(1,len(days))*100:.0f}%)\n")
        f.write(f"觸發交易中有籌碼加分者：{len(with_chumma)}/{len(triggered_all)} | 累計加分 {chumma_boost_total}\n\n")
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

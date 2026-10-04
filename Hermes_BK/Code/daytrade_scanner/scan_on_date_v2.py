#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2 回溯選股：用「指定日期收盤」的資料選股（技術面 + T86 三大法人籌碼層）。
用法：python3 scan_on_date_v2.py --date 2026-10-02 [--top 15] [--min-score 45]
"""
import argparse, csv, os, sys
from datetime import datetime, timezone
import scanner as v1
import scanner_v2 as V2

HERE = os.path.dirname(os.path.abspath(__file__))


def load_universe(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            rows.append((parts[0], parts[1] if len(parts) > 1 else ""))
    return rows


def get_full_rows(code):
    res = v1.yahoo_chart(f"{code}.TW", rng="5y")
    if not res:
        return None
    meta, rows = v1.parse_bars(res)
    return rows


def slice_rows(rows, cutoff):
    cd = cutoff.strftime("%Y-%m-%d")
    return [r for r in rows if r["date"] <= cd]


def main():
    ap = argparse.ArgumentParser(description="v2 指定日期回溯選股（技術面 + 籌碼層）")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD（含當日收盤）")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--min-score", type=int, default=v1.DEFAULT_MIN_SCORE)
    args = ap.parse_args()

    cutoff = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    universe = load_universe(os.path.join(HERE, "universe.csv"))

    print(f"[v2 選股] 日期 {args.date}（cutoff={cutoff:%Y-%m-%d}），共 {len(universe)} 檔\n")

    # 抓籌碼 cache（T86 指定日期）
    cm = V2.fetch_chumma_cache(args.date)
    print(f"[v2] T86 資料日期：{cm['data_date']} | 有法人資料的標的：{len(cm['institutional'])} 檔\n")

    results = []
    for code, name in universe:
        rows = get_full_rows(code)
        if not rows:
            continue
        sliced = slice_rows(rows, cutoff)
        r = V2.scan_one_v2(code, name, cm, rows=sliced)
        if r is None:
            continue
        if r["score"] < args.min_score:
            continue
        results.append(r)

    # 去重（universe.csv 有重複代號）
    seen = {}
    for r in results:
        seen.setdefault(r["code"], r)
    results = list(seen.values())
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:args.top]

    if not results:
        print(f"（{args.date}）無入選標的（min-score={args.min_score}）。")
        return

    hdr = (f"{'代號':>6} {'名稱':<8} {'收盤':>7} {'分':>3} {'方向':<14} "
           f"{'進場':>7} {'停損':>7} {'TP1':>7} {'TP2':>7} {'R:R':>5} "
           f"{'籌碼加分':>6} {'籌碼提示':<20}")
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        note = r.get("chumma_note", "")
        if len(note) > 18:
            note = note[:17] + "…"
        print(f"{r['code']:>6} {r['name']:<8} {r['close']:>7.1f} {r['score']:>3} "
              f"{r['direction']:<14} {r['entry']:>7.1f} {r['sl']:>7.1f} "
              f"{r['tp1']:>7.1f} {r['tp2']:>7.1f} {r['rr1']:>5} "
              f"{r.get('chumma_boost', 0):>6} {note:<20}")

    # 存 CSV（含籌碼欄位）
    out = os.path.join(HERE, f"results/scan_v2_{args.date.replace('-', '')}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["代號","名稱","收盤","分數","方向","進場","停損","TP1","TP2","R:R",
                    "籌碼加分","外資淨超(萬股)","投信淨超(萬股)","籌碼提示"])
        for r in results:
            fn = r.get("foreign_net") or 0
            inv = r.get("investor_net") or 0
            note = r.get("chumma_note", "")
            w.writerow([r["code"], r["name"], round(r["close"], 1), r["score"],
                        r["direction"], round(r["entry"], 1), round(r["sl"], 1),
                        round(r["tp1"], 1), round(r["tp2"], 1), r["rr1"],
                        r.get("chumma_boost", 0), round(fn / 10000, 1),
                        round(inv / 10000, 1), note])
    print(f"\nCSV 已存：{out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回溯選股：用「指定日期收盤」的資料選股（predict next trading day open）。
用法：python3 scan_on_date.py --date 2026-10-02 [--top 15] [--min-score 45]
"""
import argparse, csv, os, sys
from datetime import datetime, timezone
import scanner as S

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


def main():
    ap = argparse.ArgumentParser(description="指定日期回溯選股")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD（含當日收盤）")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--min-score", type=int, default=S.DEFAULT_MIN_SCORE)
    args = ap.parse_args()

    cutoff = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    universe = load_universe(os.path.join(HERE, "universe.csv"))

    print(f"[選股] 日期 {args.date}（cutoff={cutoff:%Y-%m-%d}），共 {len(universe)} 檔\n")

    results = []
    for code, name in universe:
        r = S.scan_one(code, name, cutoff=cutoff)
        if r is None:
            continue
        if r["score"] < args.min_score:
            continue
        results.append(r)

    # 去重（universe.csv 有重複代號，如台積電出現多次）
    seen = {}
    for r in results:
        seen.setdefault(r["code"], r)
    results = list(seen.values())
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:args.top]

    if not results:
        print(f"（{args.date}）無入選標的（min-score={args.min_score}）。")
        return

    # 印表
    hdr = f"{'代號':>6} {'名稱':<8} {'收盤':>7} {'分':>3} {'方向':<14} {'進場':>7} {'停損':>7} {'TP1':>7} {'TP2':>7} {'R:R':>5}"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        print(f"{r['code']:>6} {r['name']:<8} {r['close']:>7.1f} {r['score']:>3} "
              f"{r['direction']:<14} {r['entry']:>7.1f} {r['sl']:>7.1f} "
              f"{r['tp1']:>7.1f} {r['tp2']:>7.1f} {r['rr1']:>5}")

    # 存 CSV
    out = os.path.join(HERE, f"results/scan_{args.date.replace('-', '')}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["代號","名稱","收盤","分數","方向","進場","停損","TP1","TP2","R:R"])
        for r in results:
            w.writerow([r["code"], r["name"], round(r["close"], 1), r["score"],
                        r["direction"], round(r["entry"], 1), round(r["sl"], 1),
                        round(r["tp1"], 1), round(r["tp2"], 1), r["rr1"]])
    print(f"\nCSV 已存：{out}")


if __name__ == "__main__":
    main()

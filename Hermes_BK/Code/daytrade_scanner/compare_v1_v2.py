#!/usr/bin/env python3
"""Fair v1-vs-v2 comparison: identical slicing (full 5y + slice by date string),
so both use the exact same technical data. Fixes v1's UTC-cutoff timezone bug."""
import scanner as S, scanner_v2 as V2
from datetime import datetime, timezone, timedelta
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATE = "2026-10-13"   # latest COMPLETE trading day in this feed (10-12 has no finalized close)


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


def slice_rows(rows, cd):
    return [r for r in rows if r["date"] <= cd]


def dedup(res):
    seen = {}
    for r in res:
        seen.setdefault(r["code"], r)
    out = list(seen.values())
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:20]


def main():
    items = load_universe()
    print(f"[compare] date={DATE} (latest complete session), universe={len(items)} 檔\n")

    # chumma cache for the target date (T86, one call)
    cm = V2.fetch_chumma_cache(DATE)
    print(f"[compare] T86 data_date={cm['data_date']} | institutional stocks in feed={len(cm['institutional'])}\n")

    v1_res, v2_res = [], []
    for code, name in items:
        res = S.yahoo_chart(f"{code}.TW", rng="5y")
        _, rows = S.parse_bars(res)
        if not rows:
            continue
        sliced = slice_rows(rows, DATE)          # identical data for both
        r1 = S.scan_one(code, name, rows=sliced)
        if r1 and r1["score"] >= S.DEFAULT_MIN_SCORE:
            v1_res.append(r1)
        r2 = V2.scan_one_v2(code, name, cm, rows=sliced)
        if r2 and r2["score"] >= S.DEFAULT_MIN_SCORE:
            v2_res.append(r2)

    v1_res = dedup(v1_res)
    v2_res = dedup(v2_res)

    print("=" * 90)
    print(f"V1 (技術面)   through {DATE}   入選 {len(v1_res)} 檔 / 門檻 {S.DEFAULT_MIN_SCORE}")
    print("=" * 90)
    for r in v1_res:
        print(f"  {r['code']:>6} {str(r['name']):<8} 收盤{r['close']:>9.1f} 分{r['score']:>3} "
              f"{r['direction']:<16} 進{r['entry']:>8.1f} 損{r['sl']:>7.1f} TP1{r['tp1']:>7.1f} TP2{r['tp2']:>7.1f}")

    print("\n" + "=" * 90)
    print(f"V2 (技術面+T86籌碼) through {DATE}   入選 {len(v2_res)} 檔 / 門檻 {S.DEFAULT_MIN_SCORE}")
    print("=" * 90)
    for r in v2_res:
        note = (r.get("chumma_note") or "")[:24]
        print(f"  {r['code']:>6} {str(r['name']):<8} 收盤{r['close']:>9.1f} 分{r['score']:>3}(+{r.get('chumma_boost',0):>2}) "
              f"{r['direction']:<14} 進{r['entry']:>8.1f} 損{r['sl']:>7.1f} TP1{r['tp1']:>7.1f} TP2{r['tp2']:>7.1f} | {note}")

    # ---- side-by-side diff ----
    print("\n" + "=" * 90)
    print("差異對照")
    print("=" * 90)
    v1map = {r["code"]: r for r in v1_res}
    v2map = {r["code"]: r for r in v2_res}
    allcodes = sorted(set(v1map) | set(v2map))
    for c in allcodes:
        a = v1map.get(c); b = v2map.get(c)
        if a and b:
            print(f"  {c} {str(a['name']):<8} V1分{a['score']} -> V2分{b['score']} (+{b.get('chumma_boost',0)}籌碼)  都在榜")
        elif a and not b:
            print(f"  {c} {str(a['name']):<8} 僅V1入選 (V2因籌碼分數/門檻未過被剔)")
        else:
            print(f"  {c} {str(b['name']):<8} 僅V2入選 (+籌碼加分達標)")

    # save raw for report
    with open(os.path.join(HERE, "results/compare_v1_v2_20261013.txt"), "w", encoding="utf-8") as f:
        pass


if __name__ == "__main__":
    main()

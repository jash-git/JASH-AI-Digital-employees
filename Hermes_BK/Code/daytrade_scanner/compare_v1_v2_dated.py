#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fair v1-vs-v2 dated comparison: identical slicing (full 5y + slice by date string),
so both use the exact same technical data up to and INCLUDING the target date.

Fixes scan_on_date.py's UTC-cutoff timezone bug AND excludes an unsettled "today" bar
that Yahoo may already carry (slice by date string <= DATE).

資料取得（A→B 備援 + 守衛）：
  A = Yahoo（主源），B = TWSE STOCK_DAY_ALL（備援：填補 target_date 当天 Yahoo 缺的棒）。
  若兩源在 target_date 都無 universe 有效收盤 → 印「缺資料」並停跑，不產出報告。

用法：python3 compare_v1_v2_dated.py --date 2026-10-12 [--top 20] [--min-score 45]
"""
import argparse, csv, json, os, sys
from datetime import datetime, timezone
import scanner as S, scanner_v2 as V2
import data_source as DS

HERE = os.path.dirname(os.path.abspath(__file__))


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


def dedup(res, top):
    seen = {}
    for r in res:
        seen.setdefault(r["code"], r)
    out = list(seen.values())
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:top]


def main():
    global args
    ap = argparse.ArgumentParser(description="Fair dated v1-vs-v2 comparison (slice by date string)")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD（含當日收盤）")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--min-score", type=int, default=S.DEFAULT_MIN_SCORE)
    args = ap.parse_args()

    items = load_universe()
    print(f"[compare] date={args.date} (含當日收盤), universe={len(items)} 檔\n")

    cm = V2.fetch_chumma_cache(args.date)
    print(f"[compare] T86 data_date={cm['data_date']} | institutional in feed={len(cm['institutional'])}\n", file=sys.stderr)

    # ---- A→B 資料取得：Yahoo 為主（A），TWSE 為備援（B）----
    print("[compare] 抓取 Yahoo 歷史（每檔一次，主源 A）…", file=sys.stderr)
    yahoo_full = DS.collect_yahoo_full([c for c, _ in items])
    twse = DS.fetch_twse_latest_quotes()                       # 備援 B
    print(f"[compare] TWSE fallback latest={DS.determine_screen_date(twse) if twse else '無'}", file=sys.stderr)

    data_map = DS.gather_rows_union([c for c, _ in items], yahoo_full, twse, args.date)

    # ---- 守衛：兩源都無有效資料 → 停跑告知，不產出報告 ----
    covered = DS.count_covered(data_map, args.date)
    if covered == 0:
        print(f"✗ [缺資料] date={args.date} 兩源(TWSE/Yahoo)均無 universe 有效收盤，停止產出報告。")
        return

    # ---- 逐档扫描（沿用原格式）----
    v1_res, v2_res = [], []
    for code, name in items:
        rows = data_map[DS.clean_code(code)]
        if not rows or len(rows) < 20:
            continue
        r1 = S.scan_one(code, name, rows=rows)
        if r1 and r1["score"] >= args.min_score:
            v1_res.append(r1)
        r2 = V2.scan_one_v2(code, name, cm, rows=rows)
        if r2 and r2["score"] >= args.min_score:
            v2_res.append(r2)

    v1_res = dedup(v1_res, args.top)
    v2_res = dedup(v2_res, args.top)

    def fmt_v1(title, res):
        print("\n" + "=" * 96)
        print(f"{title}   through {args.date}   入選 {len(res)} 檔 / 門檻 {args.min_score}")
        print("=" * 96)
        for r in res:
            print(f"  {r['code']:>6} {str(r['name']):<8} 收盤{r['close']:>9.1f} 分{r['score']:>3} "
                  f"{r['direction']:<14} 進{r['entry']:>8.1f} 損{r['sl']:>7.1f} TP1{r['tp1']:>7.1f} TP2{r['tp2']:>7.1f} R:R{r.get('rr1',''):>5}")

    fmt_v1("V1（技術面）", v1_res)
    fmt_v1("V2（技術面 + T86 三大法人籌碼）", v2_res)

    # ---- side-by-side diff ----
    print("\n" + "=" * 96)
    print("差異對照（V1 vs V2）")
    print("=" * 96)
    v1map = {r["code"]: r for r in v1_res}
    v2map = {r["code"]: r for r in v2_res}
    allcodes = sorted(set(v1map) | set(v2map))
    only_v1, only_v2, both = [], [], []
    for c in allcodes:
        a, b = v1map.get(c), v2map.get(c)
        if a and b:
            d = b.get("chumma_boost", b["score"] - a["score"])
            note = (b.get("chumma_note") or "")[:18]
            print(f"  {c} {str(a['name']):<8} V1分{a['score']:>3} -> V2分{b['score']:>3} (+{d:>3}籌碼)  都在榜   | {note}")
            both.append((c, a["name"], a["score"], b["score"], d))
        elif a and not b:
            print(f"  {c} {str(a['name']):<8} 僅V1入選（V2因籌碼分數/門檻未過被剔）")
            only_v1.append((c, a["name"]))
        else:
            print(f"  {c} {str(b['name']):<8} 僅V2入選 (+籌碼加分達標)")
            only_v2.append((c, b["name"]))

    # ---- summary stats ----
    print("\n" + "=" * 96)
    print("統計摘要")
    print("=" * 96)
    s1 = [r["score"] for r in v1_res]
    s2 = [r["score"] for r in v2_res]
    boosts = [b.get("chumma_boost", 0) for b in v2_res]
    print(f"  V1 入選 {len(v1_res)} 檔 | 均分 {sum(s1)/len(s1):.1f} (若>0)")
    print(f"  V2 入選 {len(v2_res)} 檔 | 均分 {sum(s2)/len(s2):.1f} (若>0) | 籌碼加分總和 {sum(boosts)} | 平均 +{sum(boosts)/len(boosts):.1f}")
    print(f"  名單差異：兩者都入選 {len(both)}、僅V1 {len(only_v1)}、僅V2 {len(only_v2)}")
    risk = [(r['code'], str(r['name'])[:6], (r.get('chumma_note') or '')[:24]) for r in v2_res if '賣超' in (r.get('chumma_note') or '')]
    if risk:
        print("  ⚠ V2 標「外資大賣超 / 看空風險」的標的：")
        for c, n, note in risk:
            print(f"     {c} {n}  -> {note}")

    # ---- save raw for report ----
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    raw = {
        "date": args.date, "min_score": args.min_score, "top": args.top,
        "chumma_data_date": cm.get("data_date"),
        "v1": [{"code": r["code"], "name": r["name"], "close": round(r["close"], 1), "score": r["score"],
                "direction": r["direction"], "entry": round(r["entry"], 1), "sl": round(r["sl"], 1),
                "tp1": round(r["tp1"], 1), "tp2": round(r["tp2"], 1), "rr1": r.get("rr1"), "setup": r.get("setup")} for r in v1_res],
        "v2": [{"code": r["code"], "name": r["name"], "close": round(r["close"], 1), "score": r["score"],
                "chumma_boost": r.get("chumma_boost", 0), "direction": r["direction"], "entry": round(r["entry"], 1),
                "sl": round(r["sl"], 1), "tp1": round(r["tp1"], 1), "tp2": round(r["tp2"], 1),
                "rr1": r.get("rr1"), "chumma_note": r.get("chumma_note", ""),
                "foreign_net": (r.get("foreign_net") or 0)/10000, "investor_net": (r.get("investor_net") or 0)/10000} for r in v2_res],
        "summary": {"v1_count": len(v1_res), "v2_count": len(v2_res),
                    "both": len(both), "only_v1": len(only_v1), "only_v2": len(only_v2)},
    }
    out = os.path.join(HERE, f"results/compare_dated_{args.date.replace('-','')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    print(f"\nRaw JSON saved: {out}")


if __name__ == "__main__":
    main()

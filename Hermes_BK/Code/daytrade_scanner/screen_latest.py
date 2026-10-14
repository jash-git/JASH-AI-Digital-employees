#!/usr/bin/env python3
"""screen_latest.py：以「全市場最新已定案日」為基準的 v1/v2 對等選股比較。

與 compare_v1_v2_dated.py **完全相同的切片基底**（純 Yahoo <=D，TWSE 填 gap）。
資料取得（A→B 備援 + 守衛）：
  A = Yahoo（主源），B = TWSE STOCK_DAY_ALL（備援：填補 D 当天 Yahoo 缺的棒）。
  D = Yahoo 全覆蓋的最晚「已定案」日（A-first，過收盤≥13:30 CST 才取当日；盘中回退至最近定案日）；
     若完全無全覆蓋/已定案日 → None 停跑，不產出報告。
用法：python3 screen_latest.py [--top 15] [--min-score 45]
"""
import argparse
import csv
import os
import sys

import scanner as v1
import scanner_v2 as V2
import data_source as DS

HERE = os.path.dirname(os.path.abspath(__file__))


def load_universe(path):
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split(",")
            items.append((p[0], p[1] if len(p) > 1 else ""))
    return items


def dedup(res):
    seen = {}
    for r in res:
        seen.setdefault(r["code"], r)
    out = list(seen.values())
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:args.top]


def main():
    global args
    ap = argparse.ArgumentParser(description="以全市場最新已定案日為基準的 v1/v2 對等選股（純 Yahoo 切片）")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--min-score", type=int, default=v1.DEFAULT_MIN_SCORE)
    args = ap.parse_args()

    universe = load_universe(os.path.join(HERE, "universe.csv"))
    print("[screen] universe %d 檔" % len(universe))

    # ---- 1. 每檔抓 Yahoo 歷史一次（A 主源）----
    print("[screen] 抓取 Yahoo 歷史（每档一次）…", file=sys.stderr)
    yahoo_full = DS.collect_yahoo_full([c for c, _ in universe])

    # ---- 2. TWSE 備援（B）+ 決定 D：Yahoo 主源全覆蓋的最晚「已定案」日（A-first，過收盤才取当日）----
    twse = DS.fetch_twse_latest_quotes()                       # 備援 B
    print("[screen] TWSE fallback latest=%s" % (DS.determine_screen_date(twse) if twse else "無"), file=sys.stderr)
    ccodes = [DS.clean_code(c) for c, _ in universe]
    D = DS.resolve_screen_date_a_first(ccodes, yahoo_full, twse)
    if not D:
        print("✗ [缺資料] 兩源(TWSE/Yahoo)均無 universe 全覆蓋的交易日，停止產出報告。")
        return
    print("[screen] 權威選股日 D = %s（TWSE+Yahoo 全市場全覆蓋）" % D)

    # ---- 3. A→B 合併：Yahoo(<=D) + TWSE 填補 D 当天 ----
    data_map = DS.gather_rows_union([c for c, _ in universe], yahoo_full, twse, D)

    # ---- 完整性驗證 ----
    have = DS.count_covered(data_map, D)
    print("[screen] D 日有效收盤：%d/%d 檔" % (have, len(universe)))
    if have == 0:
        print("✗ [缺資料] D 日没有任何 universe 標的的有效收盤，資料異常。")
        return

    # ---- 4. 籌碼層（T86 該日）----
    cm = V2.fetch_chumma_cache(D)
    print("[screen] T86 籌碼日期 %s | 有法人資料 %d 檔" % (cm["data_date"], len(cm["institutional"])), file=sys.stderr)

    # ---- 5. 逐档扫描（與 compare_v1_v2_dated 完全相同）----
    v1_res, v2_res = [], []
    for code, name in universe:
        rows = data_map[DS.clean_code(code)]
        if not rows or len(rows) < 20:
            continue
        r1 = v1.scan_one(code, name, rows=rows)
        if r1 and r1["score"] >= args.min_score:
            v1_res.append(r1)
        r2 = V2.scan_one_v2(code, name, cm, rows=rows)
        if r2 and r2["score"] >= args.min_score:
            v2_res.append(r2)

    v1_res = dedup(v1_res)
    v2_res = dedup(v2_res)

    # ---- 6. 輸出（沿用原格式）----
    print("\n" + "=" * 92)
    print("V1（技術面）   D=%s   入選 %d 檔 / 門檻 %d" % (D, len(v1_res), args.min_score))
    print("=" * 92)
    for r in v1_res:
        print("  %6s %-6s 收盤%9.1f 分%3d %-18s 進%8.1f 損%7.1f TP1%7.1f TP2%7.1f"
              % (r["code"], str(r["name"])[:6], r["close"], r["score"], r["direction"],
                 r["entry"], r["sl"], r["tp1"], r["tp2"]))

    print("\n" + "=" * 92)
    print("V2（技術面+T86籌碼） D=%s   入選 %d 檔 / 門檻 %d" % (D, len(v2_res), args.min_score))
    print("=" * 92)
    for r in v2_res:
        note = (r.get("chumma_note") or "")[:22]
        print("  %6s %-6s 收盤%9.1f 分%3d(+%2d) %-16s 進%8.1f 損%7.1f TP1%7.1f TP2%7.1f | %s"
              % (r["code"], str(r["name"])[:6], r["close"], r["score"], r.get("chumma_boost", 0),
                 r["direction"], r["entry"], r["sl"], r["tp1"], r["tp2"], note))

    # ---- 差異對照 ----
    print("\n" + "=" * 92)
    print("差異對照（V1 vs V2）")
    print("=" * 92)
    m1 = {r["code"]: r for r in v1_res}
    m2 = {r["code"]: r for r in v2_res}
    for c in sorted(set(m1) | set(m2)):
        a, b = m1.get(c), m2.get(c)
        if a and b:
            print("  %s %-6s V1分%d -> V2分%d (+%d籌碼)   都在榜" % (c, str(a["name"])[:6], a["score"], b["score"], b.get("chumma_boost", 0)))
        elif a:
            print("  %s %-6s 僅V1入選（V2未達門檻）" % (c, str(a["name"])[:6]))
        else:
            print("  %s %-6s 僅V2入選 (+%d籌碼達標)" % (c, str(b["name"])[:6], b.get("chumma_boost", 0)))

    # ---- 落 CSV ----
    os.makedirs(HERE, exist_ok=True)
    with open(os.path.join(HERE, "results/screen_v1_%s.csv" % D.replace("-", "")), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["代號","名稱","收盤","分數","方向","進場","停損","TP1","TP2","R:R","策略"])
        for r in v1_res:
            w.writerow([r["code"], r["name"], round(r["close"], 1), r["score"], r["direction"],
                        round(r["entry"], 1), round(r["sl"], 1), round(r["tp1"], 1),
                        round(r["tp2"], 1), r["rr1"], r["setup"]])
    with open(os.path.join(HERE, "results/screen_v2_%s.csv" % D.replace("-", "")), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["代號","名稱","收盤","分數","籌碼加分","方向","進場","停損","TP1","TP2","籌碼提示"])
        for r in v2_res:
            w.writerow([r["code"], r["name"], round(r["close"], 1), r["score"], r.get("chumma_boost", 0),
                        r["direction"], round(r["entry"], 1), round(r["sl"], 1), round(r["tp1"], 1),
                        round(r["tp2"], 1), r.get("chumma_note", "")])
    print("\nCSV 已存：results/screen_v1_%s.csv 、 results/screen_v2_%s.csv" % (D.replace("-", ""), D.replace("-", "")))


if __name__ == "__main__":
    main()

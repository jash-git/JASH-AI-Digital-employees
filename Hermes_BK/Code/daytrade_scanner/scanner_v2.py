#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
隔天開盤當沖選股掃描器 v2  —— 整合 TWSE 官方歷史籌碼（Next-day-open day-trade scanner）

設計原則：
  * 保留 v1（scanner.py）的全部技術面邏輯不動，確保回溯結果可比較。
  * 籌碼資料來源為已驗證可用的 TWSE RWD API（免 key、回傳 JSON、支援歷史日期）：
        https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json
      → 三大法人買賣超（外資／投信／自營商，逐檔買進、賣出、買賣超），可回溯到 2019+。
  * v2 多出來的籌碼面向（對應文章四大金剛的「籌碼面」）：
        - T86 三大法人買賣超 → 外資淨超、投信連續買超、自營商動向
        - 外資持股集中度（MI_QFIIS_sort_20，最新快照）→ 機構背書

使用方式與 v1 相同（每日收盤後即時選股）：
    python3 scanner_v2.py --top 15 --min-score 45 --out-csv results/v2_today.csv

回溯測試則用 backtest_v2.py（可指定月份範圍），逐日抓「截至該日收盤」的 T86 資料。
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
import ssl
from datetime import datetime, timezone

# --------------------------------------------------------------------------- #
# 直接沿用 v1（scanner.py）的全部技術面邏輯，不重複、不改動
# --------------------------------------------------------------------------- #
import scanner as v1

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ---- TWSE RWD API 端點（已驗證：可連、免 key、回傳 JSON、支援歷史日期）----
T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"          # 三大法人買賣超（逐檔，可指定日期）
FOREIGN_TOP20_URL = "https://openapi.twse.com.tw/v1/fund/MI_QFIIS_sort_20"  # 外資持股前20名（最新快照）

# ---- v2 籌碼訊號權重（加在 v1 分數之上，總分上限仍為 100）----
CHUMMA_WEIGHTS = {
    "foreign_net_buy": 15,   # 外資當日淨買超 → 主力進場動能
    "investor_net_buy": 10,  # 投信連續/當日買超 → 散戶跟風動能
    "foreign_top20": 8,      # 外資持股前 20 名 → 機構背書（長期）
}


# --------------------------------------------------------------------------- #
# 輔助函式
# --------------------------------------------------------------------------- #
def _fetch_json(url):
    """抓 JSON，失敗回傳 None（不中斷整體掃描）。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/plain,*/*"})
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as e:  # noqa
        print(f"  [WARN] 籌碼抓取失敗 {url}: {e}", file=sys.stderr)
        return None


def _num(s):
    """把「25,569,109」或空字串轉成 int/float，失敗回傳 None。"""
    if s is None:
        return None
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _taiwan_date(t):
    """把 TWSE 日期「20260930」或「115/09/01」轉成「2026-10-02」。"""
    try:
        t = str(t).strip()
        if "/" in t:
            parts = t.split("/")
            y = int(parts[0]) + 1911
            m = int(parts[1]); d = int(parts[2])
        elif len(t) == 8 and t.isdigit():
            # YYYYMMDD（T86 date 欄位格式）
            if t.startswith("2"):
                y, m, d = int(t[:4]), int(t[4:6]), int(t[6:8])
            else:
                y = int(t[:3]) + 1911; m = int(t[3:5]); d = int(t[5:7])
        else:
            return None
        return f"{y:04d}-{m:02d}-{d:02d}"
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# 全市場籌碼表抓取（每次掃描只抓一次，之後在記憶體中按代號查）
# --------------------------------------------------------------------------- #
def fetch_chumma_cache(date_str=None):
    """回傳一個 dict，含三大法人買賣超 + 外資持股前20名的程式化索引。

    date_str: YYYY-MM-DD（回溯用）。若為 None → 抓最新交易日。
    """
    cache = {
        "institutional": {},   # code -> {foreign_net, investor_net, self_net}
        "foreign_top20": {},   # code -> SharesHeldPer(float)
        "data_date": date_str or _latest_trade_date(),
    }

    # --- T86 三大法人買賣超（逐檔）---
    # 注意：必須帶 selectType=ALL&response=json，否則只回傳 7 筆 ETF。
    if date_str:
        params = f"?date={date_str.replace('-', '')}&selectType=ALL&response=json"
    else:
        params = "?selectType=ALL&response=json"
    data = _fetch_json(T86_URL + params)
    if isinstance(data, dict):
        rows = data.get("data", [])
        cache["data_date"] = _taiwan_date(data.get("date")) or date_str
        for row in rows:
            # row 結構：[代號, 名稱, 外陸資買進, 外陸資賣出, 外陸資買賣超,
            #           外資自營商買進, 外資自營商賣出, 外資自營商買賣超,
            #           投信買進, 投信賣出, 投信買賣超, ...]
            code = str(row[0]).strip() if len(row) > 0 else ""
            if not code or not code.isdigit():
                continue
            cache["institutional"][code] = {
                "foreign_net": _num(row[4]) if len(row) > 4 else None,   # 外陸資買賣超(不含自營商)
                "investor_net": _num(row[10]) if len(row) > 10 else None,  # 投信買賣超
                "self_net": _num(row[15]) if len(row) > 15 else None,     # 自營商買賣超(避險)
            }

    # --- MI_QFIIS_sort_20：外資持股前 20 名（最新快照）---
    data = _fetch_json(FOREIGN_TOP20_URL)
    if isinstance(data, list):
        for row in data:
            code = str(row.get("Code", "")).strip()
            per = _num(row.get("SharesHeldPer"))
            if code and per is not None:
                cache["foreign_top20"][code] = per

    return cache


def _latest_trade_date():
    """抓最新交易日日期（用 T86 無參數呼叫）。"""
    data = _fetch_json(T86_URL + "?selectType=ALL&response=json")
    if isinstance(data, dict):
        return _taiwan_date(data.get("date"))
    return None


# --------------------------------------------------------------------------- #
# 籌碼訊號計算（依代號從 cache 查表）
# --------------------------------------------------------------------------- #
def chumma_signals(code, cm):
    """回傳該檔的籌碼訊號 dict。"""
    inst = cm["institutional"].get(code)
    foreign_net = inst["foreign_net"] if inst else None
    investor_net = inst["investor_net"] if inst else None
    self_net = inst["self_net"] if inst else None

    return {
        "foreign_net": foreign_net,
        "investor_net": investor_net,
        "self_net": self_net,
        "foreign_net_buy": bool(foreign_net is not None and foreign_net > 0),
        "investor_net_buy": bool(investor_net is not None and investor_net > 0),
        "foreign_top20": code in cm["foreign_top20"],
        "foreign_pct": cm["foreign_top20"].get(code),
    }


def build_short_plan(sig):
    """做空估值（mirror 長單）：entry 設在「跌破前日低」上方追空，停損在上、目標在下。"""
    p = sig["last_close"]
    atr = sig["atr"] or (p * 0.02)
    stop_dist = max(p * v1.THRESHOLDS["min_stop_pct"], atr * 0.6)
    stop_cap = p * v1.THRESHOLDS["max_stop_pct"]
    if stop_dist > stop_cap:
        stop_dist = stop_cap
    entry = sig["prev_low"] or p
    if entry >= p:
        entry = round(p * 0.997, 2)
    sl = round(entry + stop_dist, 2)      # 停損在進場上方
    risk = sl - entry
    tp1 = round(entry - risk * v1.THRESHOLDS["tp_rr_low"], 2)
    tp2 = round(entry - risk * v1.THRESHOLDS["tp_rr_high"], 2)
    return {"entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2}


# --------------------------------------------------------------------------- #
# v2 選股：沿用 v1.scan_one（技術面），再疊加籌碼層
# --------------------------------------------------------------------------- #
def scan_one_v2(code, name, cm, rows=None):
    """v2 選股：沿用 v1.scan_one（技術面），再疊加籌碼層。

    rows: 預先切片好的歷史棒（回溯用）。若為 None → 抓全歷史（每日即時選股）。
          與 v1.scan_one(rows=...) 行為一致，避免回溯時用到未來資料。
    """
    symbol = f"{code}.TW"
    if rows is None:
        meta, rows = v1.parse_bars(v1.yahoo_chart(symbol))
    else:
        meta = {}
    if not rows or len(rows) < 20:
        return None
    base_sig = v1.compute_signals(rows)
    if base_sig is None:
        return None
    base = v1.scan_one(code, name, rows=rows)   # 不變的技術面結果（或 None）
    if base is None:
        return None
    result = dict(base)                   # 複製 v1 全部欄位
    cs = chumma_signals(code, cm)
    result["_prev_low"] = base_sig["prev_low"]   # 供做空估值用（v1 未回傳）

    # ---- (A) 籌碼加分（加在 v1 分數之上，上限 100）----
    boost = 0
    if cs["foreign_net_buy"]:
        boost += CHUMMA_WEIGHTS["foreign_net_buy"]
    if cs["investor_net_buy"]:
        boost += CHUMMA_WEIGHTS["investor_net_buy"]
    if cs["foreign_top20"]:
        boost += CHUMMA_WEIGHTS["foreign_top20"]
    result["chumma_boost"] = boost
    result["score"] = min(100, base["score"] + boost)
    # 存原始籌碼數值（供 CSV/回溯使用）
    result["foreign_net"] = cs["foreign_net"]
    result["investor_net"] = cs["investor_net"]

    # ---- (B) 方向判定：在 v1「乖離過大→觀望」基礎上，加籌碼多空提示 ----
    if cs["foreign_net_buy"]:
        net_str = f"外資淨超{cs['foreign_net']/10000:.1f}萬股"
        result["chumma_note"] = f"看多（{net_str}）"
    elif cs["investor_net_buy"]:
        result["chumma_note"] = f"看多（投信買超{cs['investor_net']/10000:.1f}萬股）"
    elif cs["foreign_net"] is not None and cs["foreign_net"] < 0:
        result["chumma_note"] = f"看空風險（外資淨超{cs['foreign_net']/10000:.1f}萬股）"
    else:
        result["chumma_note"] = "籌碼中性"

    # ---- (C) 做空估值：僅在「外資賣超」時提供 ----
    if cs["foreign_net_buy"] is False and cs["foreign_net"] is not None:
        short_sig = {"last_close": base_sig["last_close"], "atr": base_sig["atr"],
                     "prev_low": result["_prev_low"]}
        sp = build_short_plan(short_sig)
        result["short_entry"] = sp["entry"]
        result["short_sl"] = sp["sl"]
        result["short_tp1"] = sp["tp1"]
        result["short_tp2"] = sp["tp2"]

    return result


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="隔天開盤當沖選股掃描器 v2（整合 TWSE 三大法人籌碼）")
    ap.add_argument("--universe", default=os.path.join(HERE, "universe.csv"), help="標的清單 CSV")
    ap.add_argument("--top", type=int, default=15, help="輸出分數最高的 N 檔")
    ap.add_argument("--min-score", type=int, default=45, help="最低入選分數")
    ap.add_argument("--out-csv", default=None, help="額外輸出 CSV 到此路徑")
    args = ap.parse_args()

    universe = v1.load_universe(args.universe)
    print(f"掃描 {len(universe)} 檔標的 …", file=sys.stderr)

    # 一次抓全市場三大法人買賣超（免 key、回傳 JSON）
    print("抓取 TWSE T86 三大法人買賣超（全市場，每項一次）…", file=sys.stderr)
    cm = fetch_chumma_cache()
    dd = cm["data_date"] or "未知"
    n_inst = len(cm["institutional"])
    print(f"  籌碼日期：{dd} | 有法人資料標的 {n_inst} 檔", file=sys.stderr)

    results = []
    for i, (code, name) in enumerate(universe):
        r = scan_one_v2(code, name, cm)
        if r and r["score"] >= args.min_score:
            results.append(r)
        if (i + 1) % 20 == 0:
            print(f"  …進度 {i+1}/{len(universe)}", file=sys.stderr)
        time.sleep(0.3)

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:args.top]

    # ---- 印表 ----
    print("\n" + "=" * 100)
    print(f"隔天開盤當沖選股結果 v2  ({datetime.now().strftime('%Y-%m-%d %H:%M')})  "
          f"入選 {len(results)} 檔 / 門檻分數 {args.min_score}  ｜ 籌碼日期 {dd}")
    print("=" * 100)
    header = (f"{'代號':<7}{'名稱':<14}{'收盤':>8}{'分':>5}{'方向':<20}"
              f"{'進場':>9}{'停損':>9}{'TP1':>9}{'TP2':>9}")
    print(header)
    print("-" * 100)
    for r in results:
        nm = (r["name"] or "")[:13]
        d = (r["direction"] or "做多")[:19]
        print(f"{r['code']:<7}{nm:<14}{r['close']:>8.1f}{r['score']:>5}{d:<20}"
              f"{r['entry']:>9.1f}{r['sl']:>9.1f}{r['tp1']:>9.1f}{r['tp2']:>9.1f}")

    # ---- 詳細說明（含籌碼面）----
    print("\n" + "-" * 100)
    print("詳細估值與操作建議：")
    for r in results:
        print(f"\n• {r['code']} {r['name']}  ｜ 分數 {r['score']}（+籌碼{r.get('chumma_boost',0)}）"
              f"  ｜ {r['direction']} （{r['setup']}）")
        print(f"   收盤 {r['close']:.1f} | 量倍(vs MA5) {r['vol_mult']}x | "
              f"MA5/10/20 = {r['ma5']:.1f}/{r['ma10']:.1f}/{r['ma20']:.1f}")
        print(f"   做多：進場觸發(前日高) {r['entry']:.1f} | 停損 {r['sl']:.1f}"
              f" (約 -{r['risk_dist']/r['entry']*100:.2f}%) | TP1 {r['tp1']:.1f}/TP2 {r['tp2']:.1f}")
        print(f"   籌碼：{r['chumma_note']}")
        if r.get("short_entry"):
            print(f"   做空估值：進場 {r['short_entry']:.1f} | 停損 {r['short_sl']:.1f}"
                  f" | TP1 {r['short_tp1']:.1f}/TP2 {r['short_tp2']:.1f}")

    # ---- CSV 輸出 ----
    if args.out_csv:
        with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["代號", "名稱", "收盤", "分數", "方向", "進場", "停損",
                        "TP1", "TP2", "R:R1", "R:R2", "策略", "外資淨超(萬股)",
                        "投信淨超(萬股)", "籌碼訊號", "籌碼提示"])
            for r in results:
                signals = []
                if r.get("chumma_boost", 0) >= CHUMMA_WEIGHTS["foreign_net_buy"]: signals.append("外資買超")
                if r.get("chumma_boost", 0) >= CHUMMA_WEIGHTS["investor_net_buy"]: signals.append("投信買超")
                if "squeeze" in (r.get("chumma_note") or ""): signals.append("軋空")
                w.writerow([r["code"], r["name"], round(r["close"], 2), r["score"],
                            r["direction"], round(r["entry"], 2), round(r["sl"], 2),
                            round(r["tp1"], 2), round(r["tp2"], 2), r["rr1"], r["rr2"],
                            r["setup"],
                            round((r.get("foreign_net") or 0) / 10000, 1),
                            round((r.get("investor_net") or 0) / 10000, 1),
                            ";".join(signals), r.get("chumma_note", "")])
        print(f"\nCSV 已輸出：{args.out_csv}")

    if not results:
        print("\n（本次無標的達門檻 → 隔日建議持幣觀望，勿盲目追高）")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
隔天開盤當沖選股掃描器 (Next-day-open day-trade scanner)

設計理念：
  把 Gemini 文章《隔天開盤當沖選股策略與技巧》的四大指標，轉成「本環境實際能自動取得」
  的可量化訊號。核心原則：先量化、再依資料可用性分級、誠實標出無法自動化者。

資料來源（本環境已驗證）：
  * Yahoo Finance chart API  ---- OHLCV（開高低收/量），可靠、可批次抓取。
      -> 可用：成交量倍增、週轉率(代理)、創波段新高、強勢收最高、均線排列、波動度(ATR)

資料來源（本環境被 bot wall，無法自動取得）：
  * TWSE 官方 API（三大法人買賣超、融券余额、券商分點買超）---- 回傳反爬 HTML / 403。
      -> 文章最核心的「籌碼面」訊號在此環境無法自動化。以下以「手動檢查清單 + 可插拔 hook」呈現，
         讓你在有 TWSE 存取權的環境（或自行架設代理）時可直接接上。

輸出：每日收盤後執行 → 列出隔日開盤適合當沖的標的 + 進場/停利/停損/方向估值表。
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
import ssl
from datetime import datetime, timedelta, timezone

# --------------------------------------------------------------------------- #
# 設定
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Yahoo chart API 主機（query1/query2 皆可，失敗時自動換）
YAHOO_HOSTS = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ---- 選股門檻（對應文章四大金剛，僅套用可自動化者）----
THRESHOLDS = {
    # 1. 成交量與流動性（硬門檻）
    "vol_mult_vs_ma5": 1.3,     # 今日量 / 近5日均量 >= 此值 → 爆量（調低以保留標的）
    "min_volume_zhang": 2000,   # 最小成交張數（流動性下限）
    # 2. 籌碼面：本環境無法自動取得 → 留空，改用手動檢查清單
    # 3. 價量與形態
    "close_to_high_ratio": 0.97,   # close/high >= 0.97 → 強勢收最高（留極短上影線）
    "new_high_lookback_days": 40,  # 收盤 >= 近 N 日高 → 創波段新高
    "above_ma20_ratio": 1.0,       # close / MA20 >= 此值 → 站上長天均線
    # 均線多頭排列：MA5 > MA10 > MA20
    # ---- 風險控管參數（文章）----
    "max_stop_pct": 0.015,     # 停損上限 1.5%
    "min_stop_pct": 0.008,     # 停損下限 0.8%
    "tp_rr_low": 1.5,          # TP1 風險報酬比
    "tp_rr_high": 2.5,         # TP2 風險報酬比
    "overheat_ratio": 1.10,    # close/MA20 超過此值 → 乖離過大，列為「開高走低」風險、降級觀望
}

# 最低入選：至少觸發的訊號數（避免要求全部同時成立）
MIN_SIGNALS_HIT = 2
DEFAULT_MIN_SCORE = 45   # 與 CLI --min-score 預設值一致

# ---- 訊號權重（用於合成分數 0-100）----
SIGNAL_WEIGHTS = {
    "volume_surge": 25,       # 成交量倍增
    "breakout_newhigh": 25,   # 創波段新高
    "strong_close_high": 15,  # 強勢收最高
    "ma_bullish_stack": 15,   # 均線多頭排列
    "uptrend_above_ma20": 10, # 站上 MA20（多頭區）
    "atr_liquidity": 10,      # 波動度適中（有波段空間又不過度）
}

# --------------------------------------------------------------------------- #
# 資料抓取
# --------------------------------------------------------------------------- #
def yahoo_chart(symbol, rng="3mo", interval="1d", cutoff=None):
    """回傳 Yahoo chart JSON 的 result[0]，失敗回傳 None。
    cutoff: datetime (tz-aware)，只保留此時間之前的棒（用於回溯測試：把資料截到「某日收盤前」）。"""
    last_err = None
    for host in YAHOO_HOSTS:
        url = (f"https://{host}/v8/finance/chart/{symbol}"
               f"?range={rng}&interval={interval}")
        if cutoff is not None:
            p1 = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp())
            p2 = int(cutoff.timestamp())
            url += f"&period1={p1}&period2={p2}"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception as e:  # noqa
            last_err = e
            continue
    print(f"  [WARN] Yahoo chart 抓取失敗 {symbol}: {last_err}", file=sys.stderr)
    return None


def parse_bars(result):
    """把 chart result 轉成 ordered list of OHLCV dicts（跳過 None）"""
    try:
        meta = result["chart"]["result"][0]["meta"]
        q = result["chart"]["result"][0]["indicators"]["quote"][0]
        ts = result["chart"]["result"][0]["timestamp"]
    except (KeyError, IndexError, TypeError):
        return None, None

    rows = []
    for t, o, h, l, c, v in zip(
            ts, q.get("open", []), q.get("high", []),
            q.get("low", []), q.get("close", []), q.get("volume", [])):
        if c is None:
            continue
        rows.append({
            "date": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"),
            "open": o, "high": h, "low": l, "close": c, "volume": v or 0,
        })
    return meta, rows


# --------------------------------------------------------------------------- #
# 技術計算
# --------------------------------------------------------------------------- #
def ma(vals, n):
    if len(vals) < n:
        return None
    return sum(vals[-n:]) / n


def atr14(rows):
    """Wilder ATR(14)，基於日線 true range。"""
    if len(rows) < 15:
        return None
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i]["high"], rows[i]["low"], rows[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    # Wilder smoothing
    atr = sum(trs[:14]) / 14
    for tr in trs[14:]:
        atr = (atr * 13 + tr) / 14
    return atr


def compute_signals(rows):
    """依文章四大指標計算各訊號布林值與技術位。回傳 dict。"""
    if not rows or len(rows) < 20:
        return None
    last = rows[-1]
    prev = rows[-2]
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]

    ma5, ma10, ma20 = ma(closes, 5), ma(closes, 10), ma(closes, 20)
    vol_ma5 = ma(vols, 5) or 1
    atr = atr14(rows)

    # 成交量倍增：今日量 / 近5日均量
    vol_mult = last["volume"] / vol_ma5 if vol_ma5 else 0

    # 創波段新高：收盤 >= 近 N 日最高收盤（或最高價）
    lb = THRESHOLDS["new_high_lookback_days"]
    recent_high = max(r["high"] for r in rows[-lb:])
    broke_new_high = last["close"] >= recent_high * 0.995

    # 強勢收最高：close/high 接近 1
    strong_close = (last["close"] / last["high"]) if last["high"] else 0
    strong_close_flag = strong_close >= THRESHOLDS["close_to_high_ratio"]

    # 均線多頭排列 MA5 > MA10 > MA20
    ma_bullish = (ma5 and ma10 and ma20 and ma5 > ma10 > ma20)

    uptrend = last["close"] >= ma20 * THRESHOLDS["above_ma20_ratio"] if ma20 else False

    # 乖離過大（開高走低風險）：收盤/MA20 超過此值 → 開高走低風險
    overheat_ratio = (last["close"] / ma20) if ma20 else 0
    overheat = overheat_ratio > THRESHOLDS["overheat_ratio"]

    return {
        "last_close": last["close"],
        "prev_close": prev["close"],
        "prev_high": prev["high"],
        "prev_low": prev["low"],
        "today_open": last["open"],
        "today_high": last["high"],
        "today_low": last["low"],
        "vol_mult": vol_mult,
        "volume_surge": vol_mult >= THRESHOLDS["vol_mult_vs_ma5"],
        "breakout_new_high": broke_new_high,
        "strong_close_ratio": strong_close,
        "strong_close_flag": strong_close_flag,
        "ma5": ma5, "ma10": ma10, "ma20": ma20,
        "ma_bullish_stack": ma_bullish,
        "uptrend_above_ma20": uptrend,
        "overheat_ratio": overheat_ratio,
        "overheat_flag": overheat,
        "atr": atr,
        "recent_high_40": recent_high,
        "volume_zhang": last["volume"],
    }


def score_signals(sig):
    """合成 0-100 分數。"""
    s = 0
    if sig["volume_surge"]:
        s += SIGNAL_WEIGHTS["volume_surge"]
    if sig["breakout_new_high"]:
        s += SIGNAL_WEIGHTS["breakout_newhigh"]
    if sig["strong_close_flag"]:
        s += SIGNAL_WEIGHTS["strong_close_high"]
    if sig["ma_bullish_stack"]:
        s += SIGNAL_WEIGHTS["ma_bullish_stack"]
    if sig["uptrend_above_ma20"]:
        s += SIGNAL_WEIGHTS["uptrend_above_ma20"]
    # 波動度適中：ATR/price 落在合理區間（約 1.5%~4%）
    p = sig["last_close"] or 1
    atr_ratio = (sig["atr"] / p) if sig["atr"] else 0
    if 0.012 <= atr_ratio <= 0.045:
        s += SIGNAL_WEIGHTS["atr_liquidity"]
    return min(100, s), round(atr_ratio, 4)


def build_trade_plan(sig):
    """依文章策略 A（突破）/ B（拉回）生成進場/停利/停損估值。"""
    p = sig["last_close"]
    atr = sig["atr"] or (p * 0.02)

    # 停損：取「百分比停損」與「ATR 停損」之大者（更保守）
    stop_pct_price = p * THRESHOLDS["min_stop_pct"]
    stop_atr_price = atr * 0.6
    stop_dist = max(stop_pct_price, stop_atr_price)
    # 但不得超過文章上限 1.5% 的價格距離（除非波動極大）
    stop_dist_cap = p * THRESHOLDS["max_stop_pct"]
    if stop_dist > stop_dist_cap:
        stop_dist = stop_dist_cap

    # 進場觸發價：突破策略用「前日高」；但若當日已收在前日高之上（突破已發生，
    # 或 Yahoo 今日棒為半日/盤後未更新），則以「當日收盤 + 0.3% 衝刺」作追單進場。
    entry = sig["prev_high"] or p
    if entry <= p:
        entry = round(p * 1.003, 2)
    sl = round(entry - stop_dist, 2)       # 停損 = 突破點下方 stop_dist
    risk = entry - sl
    tp1 = round(entry + risk * THRESHOLDS["tp_rr_low"], 2)
    tp2 = round(entry + risk * THRESHOLDS["tp_rr_high"], 2)

    rr1 = round(risk / risk, 1) if False else round(
        (tp1 - entry) / risk, 1) if risk else 0
    rr2 = round((tp2 - entry) / risk, 1) if risk else 0

    return {
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2,
        "risk_dist": round(stop_dist, 2),
        "rr1": rr1, "rr2": rr2,
        "setup": "突破(策略A)" if sig["breakout_new_high"] else "拉回找買點(策略B)",
    }


# --------------------------------------------------------------------------- #
# 籌碼面 hook（本環境無法自動取得 → 預設回傳 None）
# 若你在有 TWSE 存取權的環境執行，可實作 fetch_institutional_data() 回傳 dict：
#   {"foreign_net": float, "investor_net": float, "broker_top1": str, ...}
# --------------------------------------------------------------------------- #
def fetch_institutional_data(symbol_zh):
    """
    【本環境限制】TWSE 官方 API（bfi82u/s23 法人買賣超、s19 融券、b465 券商分點）
    在此網域回傳反爬 HTML / HTTP 403，無法自動抓取。
    此函式預設回傳 None，代表「籌碼面需人工確認」。
    接上資料源後，請在此回傳 dict（欄位見文件）。
    """
    return None


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def load_universe(path):
    """讀 universe CSV：代號,名稱。"""
    items = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip() or row[0].startswith("#"):
                continue
            code = row[0].strip()
            name = row[1].strip() if len(row) > 1 else ""
            items.append((code, name))
    return items


def scan_one(code, name, cutoff=None, rows=None):
    symbol = f"{code}.TW"
    if rows is None:
        meta, rows = parse_bars(yahoo_chart(symbol, cutoff=cutoff))
    else:
        meta = {}
    if not rows or len(rows) < 20:
        return None
    sig = compute_signals(rows)
    if sig is None:
        return None
    score, atr_ratio = score_signals(sig)
    plan = build_trade_plan(sig)

    # 方向判定：乖離過大 → 開高走低風險，降級「觀望」
    direction = "做多"
    if sig["overheat_flag"]:
        direction = "觀望(開高走低風險)"
        score = int(score * 0.6)

    # 計算觸發的訊號數（避免要求全部同時成立）
    hits = sum([sig["volume_surge"], sig["breakout_new_high"],
                sig["strong_close_flag"], sig["ma_bullish_stack"],
                sig["uptrend_above_ma20"]])

    # 門檻：至少觸發 MIN_SIGNALS_HIT 個訊號，且成交量有放大（硬流動性）
    if hits < MIN_SIGNALS_HIT or not sig["volume_surge"]:
        return None

    # 分數門檻（與 CLI --min-score 一致；scan_one 直接呼叫時也套用）
    if score < DEFAULT_MIN_SCORE:
        return None

    inst = fetch_institutional_data(code)
    return {
        "code": code, "name": name or (meta.get("shortName") if meta else ""),
        "close": sig["last_close"], "score": score, "direction": direction,
        "vol_mult": round(sig["vol_mult"], 2), "atr_ratio": atr_ratio,
        "ma5": sig["ma5"], "ma10": sig["ma10"], "ma20": sig["ma20"],
        "entry": plan["entry"], "sl": plan["sl"], "tp1": plan["tp1"],
        "tp2": plan["tp2"], "rr1": plan["rr1"], "rr2": plan["rr2"],
        "risk_dist": plan["risk_dist"],
        "setup": plan["setup"], "inst": inst,
    }


def main():
    ap = argparse.ArgumentParser(description="隔天開盤當沖選股掃描器")
    ap.add_argument("--universe", default=os.path.join(HERE, "universe.csv"),
                    help="標的清單 CSV（代號,名稱）")
    ap.add_argument("--top", type=int, default=15, help="輸出分數最高的 N 檔")
    ap.add_argument("--min-score", type=int, default=45, help="最低入選分數")
    ap.add_argument("--out-csv", default=None, help="額外輸出 CSV 到此路徑")
    args = ap.parse_args()

    universe = load_universe(args.universe)
    print(f"掃描 {len(universe)} 檔標的 …", file=sys.stderr)

    results = []
    for i, (code, name) in enumerate(universe):
        r = scan_one(code, name)
        if r and r["score"] >= args.min_score:
            results.append(r)
        if (i + 1) % 20 == 0:
            print(f"  …進度 {i+1}/{len(universe)}", file=sys.stderr)
        time.sleep(0.3)

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:args.top]

    # 印表
    print("\n" + "=" * 100)
    print(f"隔天開盤當沖選股結果  ({datetime.now().strftime('%Y-%m-%d %H:%M')})  "
          f"入選 {len(results)} 檔 / 門檻分數 {args.min_score}")
    print("=" * 100)
    header = (f"{'代號':<7}{'名稱':<16}{'收盤':>8}{'分':>5}{'方向':<16}"
              f"{'進場':>9}{'停損':>9}{'TP1':>9}{'TP2':>9}{'R:R':>7}")
    print(header)
    print("-" * 100)
    for r in results:
        nm = (r["name"] or "")[:15]
        print(f"{r['code']:<7}{nm:<16}{r['close']:>8.1f}{r['score']:>5}"
              f"{r['direction']:<16}{r['entry']:>9.1f}{r['sl']:>9.1f}"
              f"{r['tp1']:>9.1f}{r['tp2']:>9.1f}{str(r['rr1']):>7}")

    # 詳細說明（含籌碼面手動檢查）
    print("\n" + "-" * 100)
    print("詳細估值與操作建議：")
    for r in results:
        print(f"\n• {r['code']} {r['name']}  ｜ 分數 {r['score']}  ｜ {r['direction']} "
              f"（{r['setup']}）")
        print(f"   收盤 {r['close']:.1f} | 量倍(vs MA5) {r['vol_mult']}x | "
              f"MA5/10/20 = {r['ma5']:.1f}/{r['ma10']:.1f}/{r['ma20']:.1f}")
        print(f"   進場觸發(前日高) {r['entry']:.1f} | 停損 {r['sl']:.1f}"
              f" (約 -{r['risk_dist']/r['entry']*100:.2f}%)")
        print(f"   停利 TP1 {r['tp1']:.1f} / TP2 {r['tp2']:.1f} | "
              f"風險報酬比 {r['rr1']}x ~ {r['rr2']}x")
        if r["inst"]:
            print(f"   籌碼：外資淨超 {r['inst'].get('foreign_net')} / "
                  f"投信淨超 {r['inst'].get('investor_net')} / 分點 {r['inst'].get('broker_top1')}")
        else:
            print("   ⚠ 籌碼面（外資/投信買超、融券、券商分點）本環境無法自動取得，"
                  "請人工確認：")
            print("      - 三大法人當日是否買超（證交所 bfi82u / s23）")
            print("      - 是否為隔日沖大戶買超第一名（凱基台北/富邦建國/美林 → 防倒貨）")
            print("      - 融券是否增加（券增價漲 → 軋空機會）")

    # CSV 輸出
    if args.out_csv:
        with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["代號", "名稱", "收盤", "分數", "方向", "進場", "停損",
                        "TP1", "TP2", "R:R1", "R:R2", "策略"])
            for r in results:
                w.writerow([r["code"], r["name"], round(r["close"], 2), r["score"],
                            r["direction"], round(r["entry"], 2), round(r["sl"], 2),
                            round(r["tp1"], 2), round(r["tp2"], 2), r["rr1"],
                            r["rr2"], r["setup"]])
        print(f"\nCSV 已輸出：{args.out_csv}")

    if not results:
        print("\n（本次無標的達門檻 → 隔日建議持幣觀望，勿盲目追高）")


if __name__ == "__main__":
    main()

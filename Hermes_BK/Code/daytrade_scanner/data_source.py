#!/usr/bin/env python3
"""資料層（data_source.py）：Yahoo 歷史切片 + TWSE 權威日查詢，供選股/回溯使用。

本環境實測可用端點（2026-10 驗證）：
  https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL?date=YYYYMMDD
    → 回全市場（含 ETF，約 1381 檔）当日 OHLCV JSON。
    ⚠ date 參數在本環境被忽略，固定回「最新已定案交易日」（目前 = 2026-10-12）。

設計原則：
  * TWSE 給「權威、已定案的最新一天」→ determine_screen_date() 決定選股日 D。
  * Yahoo 歷史 → collect_yahoo_full() 每檔抓一次，供 v1/v2 公平切片（<=D）复用。
  * screen_latest.py 與 compare_v1_v2_dated.py 共用同一套切片基底（純 Yahoo <=D）。
"""
import json
import os
import ssl
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import scanner as S   # 复用 yahoo_chart / parse_bars

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

STOCK_DAY_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def _fetch_json(url, params="", retries=3, pause=1.5):
    """抓 JSON。重試 retries 次（指數退避短等待），處理瞬態網路/bot-wall，避免單次 blip 中斷整輪選股。
    成功回 (dict/list, None)；屢試不成回 (None, error_msg)。"""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url + ("?" + params if params else ""),
                headers={"User-Agent": UA, "Accept": "application/json,*/*"})
            with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
                return json.loads(r.read().decode("utf-8", "ignore")), None
        except Exception as e:  # noqa
            last_err = e
            if attempt < retries - 1:
                time.sleep(pause * (attempt + 1))
    return None, str(last_err)


def _to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except (ValueError, TypeError):
        return None


def twse_date_to_iso(t):
    """TWSE 日期「1151012」（民國3位年+月+日）或「20261012」→「2026-10-12」。"""
    t = str(t).strip()
    if not t.isdigit():
        return None
    if len(t) == 7:            # yyyMMdd 民國
        y, m, d = int(t[:3]) + 1911, int(t[3:5]), int(t[5:7])
    elif len(t) == 8 and t.startswith("2"):   # yyyyMMdd 公元
        y, m, d = int(t[:4]), int(t[4:6]), int(t[6:8])
    elif len(t) == 8:          # yyyMMdd 民國（補強）
        y, m, d = int(t[:3]) + 1911, int(t[3:5]), int(t[5:7])
    else:
        return None
    return "%04d-%02d-%02d" % (y, m, d)


def clean_code(code):
    """「02330」→「2330」（至少保留一位）。"""
    c = str(code).strip().lstrip("0")
    return c or "0"


def fetch_twse_latest_quotes():
    """回傳 {code: {'date','name','open','high','low','close','volume'}, ...}，失敗回傳 None。"""
    data, err = _fetch_json(STOCK_DAY_ALL_URL)
    if not isinstance(data, list) or not data:
        print("  [WARN] TWSE STOCK_DAY_ALL 抓取失敗:", err)
        return None
    out = {}
    for row in data:
        code = clean_code(row.get("Code"))
        q = {
            "date": twse_date_to_iso(row.get("Date")),
            "name": row.get("Name", ""),
            "open": _to_float(row.get("OpeningPrice")),
            "high": _to_float(row.get("HighestPrice")),
            "low": _to_float(row.get("LowestPrice")),
            "close": _to_float(row.get("ClosingPrice")),
            "volume": int(_to_float(row.get("TradeVolume")) or 0),
        }
        out[code] = q
    return out


def determine_screen_date(twse_quotes):
    """從 TWSE 決定可安全選股的最新交易日 D（最晚且有資料的日期）。"""
    if not twse_quotes:
        return None
    dates = sorted({q["date"] for q in twse_quotes.values() if q["date"]})
    return dates[-1] if dates else None


def collect_yahoo_full(codes):
    """每檔抓 Yahoo 1y 歷史一次，回傳 {clean_code: [rows asc]}（parse_bars 已跳 None 收盤）。
    供 v1/v2 公平切片（<=D）复用，避免重複抓取。"""
    out = {}
    for code in codes:
        cc = clean_code(code)
        res = S.yahoo_chart("%s.TW" % cc, rng="5y")
        if not res:
            out[cc] = []
            continue
        _, rows = S.parse_bars(res)
        rows = [r for r in rows if r.get("close") is not None]
        rows.sort(key=lambda r: r["date"])
        out[cc] = rows
    return out


def twse_row_from_quote(q):
    """TWSE 單檔当日棒 → Yahoo row 格式（{date,open,high,low,close,volume}）。"""
    return {
        "date": q.get("date"),
        "open": _to_float(q.get("open")),
        "high": _to_float(q.get("high")),
        "low": _to_float(q.get("low")),
        "close": _to_float(q.get("close")),
        "volume": int(_to_float(q.get("volume")) or 0),
    }


def gather_rows_union(codes, yahoo_full, twse_quotes, target_date):
    """A→B 資料取得：Yahoo 為主（A），TWSE 為備援（B）。
       每档 = Yahoo 歷史(<=target_date)；若当天(target_date) Yahoo 缺有效收盤，
       用 TWSE 当日棒補上（填 gap）。回傳 {clean_code: [rows asc]}。"""
    twse_quotes = twse_quotes or {}
    out = {}
    for code in codes:
        cc = clean_code(code)
        rows = [dict(r) for r in yahoo_full.get(cc, []) if r["date"] <= target_date]
        last = rows[-1] if rows else None
        need_fill = (not last) or last["date"] != target_date or last.get("close") is None
        if need_fill:
            q = twse_quotes.get(cc)
            if q and q.get("date") == target_date and _to_float(q.get("close")) is not None:
                rows.append(twse_row_from_quote(q))
                rows.sort(key=lambda r: r["date"])
        out[cc] = rows
    return out


def count_covered(data_map, target_date):
    """target_date 有有效收盤的檔數（A+B 合併後）。"""
    n = 0
    for cc, rows in data_map.items():
        if any(r["date"] == target_date and r.get("close") is not None for r in rows):
            n += 1
    return n


def resolve_screen_date_union(codes, yahoo_full, twse_quotes):
    """A→B 選股日（Yahoo 為主、TWSE 為已定案天花板）：
       D = 兩源(TWSE+Yahoo)合起來全覆蓋的最晚交易日，但不超過 TWSE 權威已定案日。
       （TWSE 不發未定案當日線 ⇒ 截断可排除 Yahoo 可能多出的未定案当日棒，避免 look-ahead。）
       若 TWSE 不可用 → 以 Yahoo 最晚全覆蓋日為 D；完全無 → None。"""
    ccodes = [clean_code(c) for c in codes]
    combined = {cc: set() for cc in ccodes}
    for cc in ccodes:
        for r in yahoo_full.get(cc, []):
            if r.get("close") is not None:
                combined[cc].add(r["date"])
    tL = determine_screen_date(twse_quotes or {})     # TWSE 權威已定案日（天花板）
    bound = tL if tL else "9999-12-31"
    for cc in ccodes:
        q = (twse_quotes or {}).get(cc)
        if q and q.get("date"):
            combined[cc].add(q["date"])
    all_dates = sorted({d for cc in ccodes for d in combined[cc] if d <= bound}, reverse=True)
    return next((d for d in all_dates if all(d in combined[cc] for cc in ccodes)), None)


# ---------------------------------------------------------------------------
# A-first 選股日解析（2026-10-14 更新：以 Yahoo 主源已定案最晚日為準，TWSE 不再當天花板）
# ---------------------------------------------------------------------------

MARKET_CLOSE_CST = 13 * 60 + 30   # 台股收盤 13:30（分鐘）


def _now_cst():
    """目前台灣時間（UTC+8）。"""
    return datetime.now(timezone(timedelta(hours=8)))


def _is_day_settled(date_str, now_cst):
    """date_str(YYYY-MM-DD) 是否為「已定案日」：
       - 非未來日期；且（早於今日，或今日已过 13:30 收盤）。
       → 盘中不取当日線，避免用到未定案的當日棒（look-ahead）。"""
    today = now_cst.strftime("%Y-%m-%d")
    if date_str > today:
        return False
    if date_str == today:
        return (now_cst.hour * 60 + now_cst.minute) >= MARKET_CLOSE_CST
    return True


def resolve_screen_date_a_first(codes, yahoo_full, twse_quotes=None):
    """A-first 選股日（Yahoo 為主源）：D = Yahoo 全覆蓋的最晚「已定案」交易日。
       - TWSE 不再當天花板；僅在 gather_rows_union 補 D 缺棒時作备援（A→B）。
       - 過收盤(≥13:30 CST)才視「今日」為定案；盘中回退到最近已定案日。
       - 需所有 universe 檔於 D 皆有 Yahoo 有效收盤（維持 v1/v2 對等切片）。
       - 完全無全覆蓋日 → None（不產報告，符合「兩源皆無資料則停跑」）。
       （取代舊的 resolve_screen_date_union：後者以 TWSE 已定案日為天花板，TWSE 落後時
        會錯誤地把 D 往下退，違反 A-first。screen_latest 現改用本函式。）"""
    ccodes = [clean_code(c) for c in codes]
    per_date = {cc: {r["date"] for r in yahoo_full.get(cc, []) if r.get("close") is not None}
                for cc in ccodes}
    covered_all = sorted(
        {d for d in set().union(*per_date.values()) if all(d in per_date[cc] for cc in ccodes)},
        reverse=True)
    now_cst = _now_cst()
    for d in covered_all:                       # 由晚到早，取第一個已定案日
        if _is_day_settled(d, now_cst):
            return d
    return None                                 # 無已定案日 → 停跑不產報告

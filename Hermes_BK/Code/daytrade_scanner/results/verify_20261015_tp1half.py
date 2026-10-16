# -*- coding: utf-8 -*-
"""驗證 2026-10-14 選股報告 → 對照 2026-10-15 實際盤價（TP1半倉拚TP2 規則）。"""
import sys, json
sys.path.insert(0, "/home/vblinux/daytrade_scanner")
from scanner import yahoo_chart, parse_bars
from backtest_tp1half_tp2 import evaluate, RATE_BUY, RATE_SELL

# 昨日（10-14）報告入選 8 檔的進場/停損/TP1/TP2（V1=V2，名單相同）
picks = [
    {"code": "2357", "name": "華碩", "entry": 993.0, "sl": 978.1, "tp1": 1015.2, "tp2": 1030.1},
    {"code": "1605", "name": "華新", "entry": 40.8, "sl": 40.2, "tp1": 41.7, "tp2": 42.3},
    {"code": "2349", "name": "錸德", "entry": 11.1, "sl": 11.0, "tp1": 11.4, "tp2": 11.6},
    {"code": "3034", "name": "聯詠", "entry": 561.7, "sl": 553.3, "tp1": 574.3, "tp2": 582.7},
    {"code": "2379", "name": "瑞昱", "entry": 780.3, "sl": 768.7, "tp1": 797.8, "tp2": 809.5},
    {"code": "2353", "name": "宏碁", "entry": 32.2, "sl": 31.8, "tp1": 32.9, "tp2": 33.3},
    {"code": "2352", "name": "佳世達", "entry": 29.6, "sl": 29.2, "tp1": 30.3, "tp2": 30.7},
    {"code": "2912", "name": "統一超", "entry": 220.2, "sl": 218.4, "tp1": 222.8, "tp2": 224.6},
]

def get_bar(code):
    sym = f"{code}.TW"
    result = yahoo_chart(sym, rng="5d", interval="1d")
    if not result:
        return None
    meta, rows = parse_bars(result)
    if not rows:
        return None
    return rows[-1], rows

print(f"{'代號':6} {'名稱':6} {'進場':>8} {'停損':>7} {'TP1':>7} {'TP2':>7} | {'O':>8} {'H':>8} {'L':>8} {'C':>8} | 結果")
print("-" * 96)

total_gross = 0.0
total_net = 0.0
triggered_n = 0
win_n = 0
loss_n = 0
not_triggered = []
rows_out = []

for p in picks:
    bar, rows = get_bar(p["code"])
    if bar is None:
        print(f"{p['code']:6} {p['name']:6} {'抓取失敗'}")
        continue
    date = bar["date"]
    sig = {"entry": p["entry"], "sl": p["sl"], "tp1": p["tp1"], "tp2": p["tp2"]}
    r = evaluate(sig, bar)
    if not r.get("triggered"):
        tag = "未觸發（進不去）"
        print(f"{p['code']:6} {p['name']:6} {p['entry']:8.1f} {p['sl']:7.1f} {p['tp1']:7.1f} {p['tp2']:7.1f} | "
              f"{bar['open']:8.1f} {bar['high']:8.1f} {bar['low']:8.1f} {bar['close']:8.1f} | ⚪ {tag}")
        not_triggered.append(p["name"])
        continue
    triggered_n += 1
    total_gross += r["pnl"]
    total_net += r["pnl_net"]
    if r["profit"]:
        win_n += 1
    else:
        loss_n += 1
    tag = r["outcome"]
    pct = r["pnl"] / p["entry"] * 100
    print(f"{p['code']:6} {p['name']:6} {p['entry']:8.1f} {p['sl']:7.1f} {p['tp1']:7.1f} {p['tp2']:7.1f} | "
          f"{bar['open']:8.1f} {bar['high']:8.1f} {bar['low']:8.1f} {bar['close']:8.1f} | 📊 {tag}: "
          f"毛{r['pnl']:+.2f}/淨{r['pnl_net']:+.2f} ({pct:+.2f}%)")
    rows_out.append({"code": p["code"], "name": p["name"], "date": date,
                     "entry": p["entry"], "sl": p["sl"], "tp1": p["tp1"], "tp2": p["tp2"],
                     "O": bar["open"], "H": bar["high"], "L": bar["low"], "C": bar["close"],
                     "outcome": r["outcome"], "pnl_gross": r["pnl"], "pnl_net": r["pnl_net"],
                     "pct": pct})

print("-" * 96)
print(f"入選 {len(picks)} 檔｜實際觸發 {triggered_n} 筆｜獲利 {win_n} / 虧損 {loss_n}")
print(f"累積毛 PnL = {total_gross:+.2f} 元/股")
print(f"累積淨 PnL（扣當沖最高費）= {total_net:+.2f} 元/股")

with open("/home/vblinux/daytrade_scanner/results/verify_20261015_tp1half.json", "w") as f:
    json.dump({"date": rows_out[0]["date"] if rows_out else None,
               "rows": rows_out,
               "triggered": triggered_n, "win": win_n, "loss": loss_n,
               "gross": round(total_gross, 2), "net": round(total_net, 2)}, f, ensure_ascii=False, indent=2)

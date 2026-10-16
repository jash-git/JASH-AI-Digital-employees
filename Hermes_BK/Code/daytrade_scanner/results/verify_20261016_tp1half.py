# -*- coding: utf-8 -*-
"""驗證 2026-10-15 選股報告 → 對照 2026-10-16 實際盤價（TP1半倉拚TP2 規則）。"""
import sys, json
sys.path.insert(0, "/home/vblinux/daytrade_scanner")
from scanner import yahoo_chart, parse_bars
from backtest_tp1half_tp2 import evaluate, RATE_BUY, RATE_SELL

# 昨日（10-15）報告入選 8 檔的進場/停損/TP1/TP2（V1=V2，名單相同）
picks = [
    {"code": "4904", "name": "遠傳", "entry": 113.3, "sl": 112.1, "tp1": 115.2, "tp2": 116.4},
    {"code": "3034", "name": "聯詠", "entry": 566.7, "sl": 558.2, "tp1": 579.4, "tp2": 587.9},
    {"code": "2379", "name": "瑞昱", "entry": 779.0, "sl": 767.5, "tp1": 796.2, "tp2": 807.6},
    {"code": "2377", "name": "微星", "entry": 159.5, "sl": 157.1, "tp1": 163.1, "tp2": 165.4},
    {"code": "2912", "name": "統一超", "entry": 224.7, "sl": 222.9, "tp1": 227.3, "tp2": 229.1},
    {"code": "2330", "name": "台積電", "entry": 2535.0, "sl": 2510.1, "tp1": 2572.4, "tp2": 2597.4},
    {"code": "2395", "name": "研華", "entry": 721.0, "sl": 710.5, "tp1": 736.7, "tp2": 747.2},
    {"code": "1605", "name": "華新", "entry": 41.1, "sl": 40.5, "tp1": 42.0, "tp2": 42.5},
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
if triggered_n:
    print(f"勝率 = {win_n/triggered_n*100:.1f}%")
print(f"累積毛 PnL = {total_gross:+.2f} 元/股")
print(f"累積淨 PnL（扣當沖最高費）= {total_net:+.2f} 元/股")

with open("/home/vblinux/daytrade_scanner/results/verify_20261016_tp1half.json", "w") as f:
    json.dump({"date": rows_out[0]["date"] if rows_out else None,
               "picks_date": "2026-10-15", "exec_date": "2026-10-16",
               "rows": rows_out,
               "summary": {"picked": len(picks), "triggered": triggered_n,
                           "wins": win_n, "losses": loss_n,
                           "gross": total_gross, "net": total_net}}, f, ensure_ascii=False, indent=2)

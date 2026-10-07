#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【TP1-only 回溯】嚴格遵守「開倉 + 停損 + TP1 停利」規則，不考慮滑點。

與 backtest_v2.py 的差異：
  * 出場只分三種 —— 達TP1（獲利了結）、停損（洗出）、收盤未達任一目標則以收盤了結。
  * 不看 TP2（用戶指定「TP1 停利」）。
  * 不扣手續費/滑點（純價格對價格）。

v1 與 v2 的實際交易 PnL 完全相同：籌碼加分只改 score，不改 entry/sl/tp1/tp2，
也不會增刪入選名單（加分制）。故此處用 v1.scan_one。

執行：python3 backtest_tp1_only.py --start-month 1 --end-month 9
"""
import argparse, csv, os, sys
from datetime import datetime, timezone, timedelta
import scanner as S

HERE = os.path.dirname(os.path.abspath(__file__))


def compute_range(start_month, end_month):
    start_day = datetime(2026, start_month, 1, tzinfo=timezone.utc)
    em = end_month + 1
    ey = 2026 + (em - 1) // 12
    em = (em - 1) % 12 + 1
    end_day = datetime(ey, em, 1, tzinfo=timezone.utc)
    return start_day, end_day


def trading_days(start_day, end_day):
    days = []
    d = start_day.date()
    while d < end_day.date():
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def get_full_rows(code):
    res = S.yahoo_chart(f"{code}.TW", rng="5y")
    if not res:
        return None
    meta, rows = S.parse_bars(res)
    return rows


def slice_rows(rows, target_date):
    td = target_date.strftime("%Y-%m-%d")
    return [r for r in rows if r["date"] <= td]


def get_next_bar(rows, after_date):
    ad = after_date.strftime("%Y-%m-%d")
    for r in rows:
        if r["date"] > ad:
            return r
    return None


def simulate_tp(sig, bar, tp_target):
    """只考慮 TP（tp1 或 tp2）+ 停損。未達任一目標則以收盤了結（當沖無法過夜）。"""
    entry = sig["entry"]; sl = sig["sl"]
    tp = sig["tp2"] if tp_target == "tp2" else sig["tp1"]
    o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
    triggered = (h >= entry) or (o > entry)
    if not triggered:
        return {"triggered": False}
    if l <= sl:
        pnl, outcome = sl - entry, "停損"
    elif h >= tp:
        pnl, outcome = tp - entry, f"達{tp_target.upper()}"
    else:
        pnl, outcome = c - entry, f"收盤了結(未達{tp_target.upper()}/SL)"
    return {"triggered": True, "pnl": round(pnl, 2),
            "outcome": outcome, "profit": pnl > 0}


def main():
    ap = argparse.ArgumentParser(description="TP-only 當沖回溯（開倉+停損+TP，無滑點")
    ap.add_argument("--start-month", type=int, default=1)
    ap.add_argument("--end-month", type=int, default=9)
    ap.add_argument("--tp", choices=["tp1", "tp2"], default="tp1",
                    help="出場目標：tp1 或 tp2（default: tp1）")
    args = ap.parse_args()

    start_day, end_day = compute_range(args.start_month, args.end_month)
    universe = S.load_universe(os.path.join(HERE, "universe.csv"))
    days = trading_days(start_day, end_day)
    print(f"[TP1-only] {start_day.date()} → {end_day.date()}（不含），共 {len(days)} 個交易日")

    full = {}
    for code, name in universe:
        rows = get_full_rows(code)
        if rows:
            full[code] = {"name": name, "rows": rows}
    tp_target = args.tp
    print(f"[TP-only] 出場目標：{tp_target.upper()} | 成功抓取 {len(full)} 檔\n")

    all_records = []
    for d in days:
        td = d.strftime("%Y-%m-%d")
        for code, info in full.items():
            rows = slice_rows(info["rows"], d)
            r = S.scan_one(code, info["name"], rows=rows)
            if r is None:
                continue
            bar = get_next_bar(info["rows"], d)
            if bar is None:
                continue
            res = simulate_tp(r, bar, tp_target)
            all_records.append({"date": td, "next_date": bar["date"],
                                "code": code, "name": info["name"],
                                "score": r["score"], "entry": r["entry"],
                                "sl": r["sl"], "tp1": r["tp1"],
                                "prev_close": r["close"],
                                "o": bar["open"], "h": bar["high"],
                                "l": bar["low"], "c": bar["close"], **res})

    n_total = len(all_records)
    triggered = [r for r in all_records if r["triggered"]]
    hit_tp = [r for r in triggered if r["outcome"] == f"達{tp_target.upper()}"]
    stopped = [r for r in triggered if r["outcome"] == "停損"]
    closed = [r for r in triggered if r["outcome"] == f"收盤了結(未達{tp_target.upper()}/SL)"]
    profitable = [r for r in triggered if r["profit"]]

    total_pnl = sum(r["pnl"] for r in triggered)
    win_pnl = sum(r["pnl"] for r in hit_tp)
    loss_pnl = sum(r["pnl"] for r in stopped)
    close_pnl = sum(r["pnl"] for r in closed)

    month_label = f"{args.start_month:02d}~{args.end_month:02d}"
    csv_out = os.path.join(HERE, f"results/backtest_{tp_target}_{month_label}.csv")
    txt_out = os.path.join(HERE, f"results/backtest_{tp_target}_{month_label}_summary.txt")

    print("=" * 90)
    print(f"【{tp_target.upper()}-only 回溯結果】2026-{month_label}（共 {len(days)} 個交易日，無滑點/手續費）")
    print("=" * 90)
    print(f"全部入選筆數：{n_total}")
    print(f"實際觸發進場：{len(triggered)} 筆 ({len(triggered)/max(1,n_total)*100:.0f}%)")
    print(f"未觸發（錯過）：{n_total - len(triggered)} 筆\n")

    if triggered:
        print(f"── 出場分佈 ──")
        print(f"達{tp_target.upper()}（獲利了結）：{len(hit_tp)} 筆 ({len(hit_tp)/len(triggered)*100:.1f}%)")
        print(f"停損洗出        ：{len(stopped)} 筆 ({len(stopped)/len(triggered)*100:.1f}%)")
        print(f"收盤未達目標    ：{len(closed)} 筆 ({len(closed)/len(triggered)*100:.1f}%)")
        print()
        # 勝率：以「實際觸發進場」為分母（含收盤了結）
        wr_all = len(profitable) / len(triggered) * 100
        # 勝率：僅計 SL/TP 有明確出場者（排除收盤了結）
        resolved = hit_tp + stopped
        wr_resolved = sum(1 for r in resolved if r["profit"]) / max(1, len(resolved)) * 100
        print(f"── 勝率 ──")
        print(f"獲利筆數：{len(profitable)}/{len(triggered)} = {wr_all:.1f}%   （分母=全部觸發）")
        print(f"獲利筆數：{sum(1 for r in resolved if r['profit'])}/{len(resolved)} = {wr_resolved:.1f}%   （分母=僅SL/TP明確出場）")
        print()
        print(f"── 損益（元/股，毛）──")
        print(f"累積 PnL：{total_pnl:+.2f} 元/股")
        print(f"  → 達{tp_target.upper()}貢獻：{win_pnl:+.2f} 元/股")
        print(f"  → 停損虧損：{loss_pnl:+.2f} 元/股")
        print(f"  → 收盤了結：{close_pnl:+.2f} 元/股")
        print(f"平均每筆觸發 PnL：{total_pnl/len(triggered):+.2f} 元/股")
        avg_win = win_pnl / max(1, len(hit_tp))
        avg_loss = loss_pnl / max(1, len(stopped))
        print(f"平均獲利（達{tp_target.upper()}）：{avg_win:+.2f} 元/股 | 平均虧損（停損）：{avg_loss:+.2f} 元/股")
        if avg_loss != 0:
            print(f"盈亏比（获利均/亏损均绝对值）：{abs(avg_win/avg_loss):.2f}")

    # ---- CSV ----
    os.makedirs(os.path.dirname(csv_out), exist_ok=True)
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["日期","次日","代號","名稱","分數","進場","停損","TP1",
                    "次日開","次日高","次日低","次日收","是否觸發","結果","PnL(元/股)"])
        for r in all_records:
            w.writerow([r["date"], r["next_date"], r["code"], r["name"], r["score"],
                        round(r["entry"], 2), round(r["sl"], 2), round(r["tp1"], 2),
                        r["o"], r["h"], r["l"], r["c"], r["triggered"],
                        r["outcome"] if r["triggered"] else "未觸發",
                        r.get("pnl", "")])
    print(f"\nCSV 已存：{csv_out}")

    # ---- TXT ----
    with open(txt_out, "w", encoding="utf-8") as f:
        f.write(f"【{tp_target.upper()}-only 回溯測試報告】2026 年 {month_label} 月（無滑點/手續費）\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"交易日數：{len(days)}\n全部入選筆數：{n_total}\n實際觸發進場：{len(triggered)} ({len(triggered)/max(1,n_total)*100:.0f}%)\n\n")
        if triggered:
            f.write(f"達{tp_target.upper()}：{len(hit_tp)} 筆 | 停損：{len(stopped)} 筆 | 收盤了結：{len(closed)} 筆\n")
            f.write(f"勝率(分母=全部觸發)：{wr_all:.1f}%\n")
            f.write(f"勝率(分母=僅SL/TP)：{wr_resolved:.1f}%\n")
            f.write(f"累積PnL：{total_pnl:+.2f} 元/股\n")
            f.write(f"平均每筆：{total_pnl/len(triggered):+.2f} 元/股\n")
    print(f"摘要已存：{txt_out}")


if __name__ == "__main__":
    main()

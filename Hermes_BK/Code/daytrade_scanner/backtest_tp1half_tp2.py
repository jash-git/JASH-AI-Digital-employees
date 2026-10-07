#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【TP1 半倉停利 + 另一半拚 TP2】回溯：嚴格遵守「開倉 + 停損 + TP1 先收一半 + 剩下一半跑 TP2」規則，無滑點。

出場模型（每檔拆成兩個獨立半倉）：
  * 半倉 A（TP1 目標）：h >= tp1 → 在 TP1 獲利了結；否則 l <= sl → 停損；否則收盤了結。
  * 半倉 B（TP2 目標）：h >= tp2 → 在 TP2 獲利了結；否則 l <= sl → 停損；否則收盤了結。
  * 單筆 PnL = 半倉A + 半倉B，各乘 0.5 權重。

與 backtest_tp1_only.py / backtest_tp2_only.py 的差異：
  * TP1-only：全部在 TP1 收手（盈亏比 1.91）。
  * TP2-only：全部跑 TP2（盈亏比 3.47，但只有 1/4 達標）。
  * TP1半倉+TP2拚盤：一半鎖 TP1 利潤、一半博 TP2 —— 兼顧「鎖定」與「放大」。

v1 與 v2 實際交易 PnL 完全相同（籌碼加分不改 entry/sl/tp，也不增刪名單）。

執行：python3 backtest_tp1half_tp2.py --start-month 1 --end-month 9
"""
import argparse, csv, os
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


def evaluate(sig, bar):
    """半倉 TP1 + 拚 TP2（A 賣掉後 B 移到保本停損）。回傳 {triggered, pnl, outcome, profit}。

    與原版差異：當 A 在 TP1 獲利了結後，B 的停損從原 sl 上移到「保本 = entry」。
    → 一旦 A 鎖利成功，B 最多平手（b=0），絕不虧 → 凡達 TP1 者皆為贏。"""
    entry = sig["entry"]; sl = sig["sl"]; tp1 = sig["tp1"]; tp2 = sig["tp2"]
    o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]

    # 進場觸發條件（與其它回溯一致）：當日摸到或高過進場價
    triggered = (h >= entry) or (o > entry)
    if not triggered:
        return {"triggered": False}

    # 半倉 A：TP1 目標（先檢查 TP1，再停損，否則收盤）
    a_hit_tp1 = h >= tp1
    if a_hit_tp1:
        a = 0.5 * (tp1 - entry); a_tag = "TP1"
    elif l <= sl:
        a = 0.5 * (sl - entry); a_tag = "SL"
    else:
        a = 0.5 * (c - entry); a_tag = "收"

    # 半倉 B：TP2 目標。若 A 已在 TP1 賣掉 → B 停損移到保本(entry)；否則用原 sl。
    b_sl = entry if a_hit_tp1 else sl
    if h >= tp2:
        b = 0.5 * (tp2 - entry); b_tag = "TP2"
    elif l <= b_sl:
        b = 0.5 * (b_sl - entry); b_tag = "SL"   # 保本停損時 b=0（平手）
    else:
        b = 0.5 * (c - entry); b_tag = "收"

    pnl = round(a + b, 2)
    # 結果分類（優先級：TP2 > TP1>SL/收 > 全停損）
    if h >= tp2:
        outcome = "達TP1+達TP2"
    elif h >= tp1:
        outcome = f"達TP1(另一半{b_tag})"   # b_tag=SL 表示保本平手、收=收盤了結
    elif l <= sl:
        outcome = "停損"
    else:
        outcome = "收盤了結"

    return {"triggered": True, "pnl": pnl, "outcome": outcome, "profit": pnl > 0}


def main():
    ap = argparse.ArgumentParser(description="TP1半倉停利+另一半拚TP2回溯（無滑點")
    ap.add_argument("--start-month", type=int, default=1)
    ap.add_argument("--end-month", type=int, default=9)
    args = ap.parse_args()

    start_day, end_day = compute_range(args.start_month, args.end_month)
    universe = S.load_universe(os.path.join(HERE, "universe.csv"))
    days = trading_days(start_day, end_day)
    print(f"[TP1半倉+TP2] {start_day.date()} → {end_day.date()}（不含），共 {len(days)} 個交易日")

    full = {}
    for code, name in universe:
        rows = get_full_rows(code)
        if rows:
            full[code] = {"name": name, "rows": rows}
    print(f"[TP1半倉+TP2] 成功抓取 {len(full)} 檔\n")

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
            res = evaluate(r, bar)
            all_records.append({"date": td, "next_date": bar["date"],
                                "code": code, "name": info["name"],
                                "score": r["score"], "entry": r["entry"],
                                "sl": r["sl"], "tp1": r["tp1"], "tp2": r["tp2"],
                                "prev_close": r["close"],
                                "o": bar["open"], "h": bar["high"],
                                "l": bar["low"], "c": bar["close"], **res})

    n_total = len(all_records)
    triggered = [r for r in all_records if r["triggered"]]
    # 結果分類計數
    hit_tp2 = [r for r in triggered if r["outcome"] == "達TP1+達TP2"]
    tp1_then_breakeven = [r for r in triggered if r["outcome"] == "達TP1(另一半SL)"]
    tp1_then_close = [r for r in triggered if r["outcome"].startswith("達TP1(另一半收")]
    stopped = [r for r in triggered if r["outcome"] == "停損"]
    closed = [r for r in triggered if r["outcome"] == "收盤了結"]
    profitable = [r for r in triggered if r["profit"]]

    total_pnl = sum(r["pnl"] for r in triggered)
    win_tp2 = sum(r["pnl"] for r in hit_tp2)
    win_tp1_then_breakeven = sum(r["pnl"] for r in tp1_then_breakeven)
    win_tp1_then_close = sum(r["pnl"] for r in tp1_then_close)
    loss_stopped = sum(r["pnl"] for r in stopped)
    close_pnl = sum(r["pnl"] for r in closed)

    month_label = f"{args.start_month:02d}~{args.end_month:02d}"
    csv_out = os.path.join(HERE, f"results/backtest_tp1half_{month_label}.csv")
    txt_out = os.path.join(HERE, f"results/backtest_tp1half_{month_label}_summary.txt")

    print("=" * 90)
    print(f"【TP1半倉停利+拚TP2（A賣後B保本）回溯結果】2026-{month_label}（共 {len(days)} 個交易日，無滑點/手續費）")
    print("=" * 90)
    print(f"全部入選筆數：{n_total}")
    print(f"實際觸發進場：{len(triggered)} 筆 ({len(triggered)/max(1,n_total)*100:.0f}%)")
    print(f"未觸發（錯過）：{n_total - len(triggered)} 筆\n")

    if triggered:
        print(f"── 出場分佈 ──")
        print(f"達TP1+達TP2：{len(hit_tp2)} 筆 ({len(hit_tp2)/len(triggered)*100:.1f}%)")
        print(f"達TP1(另一半保本平手)：{len(tp1_then_breakeven)} 筆 ({len(tp1_then_breakeven)/len(triggered)*100:.1f}%)")
        print(f"達TP1(另一半收盤)：{len(tp1_then_close)} 筆 ({len(tp1_then_close)/len(triggered)*100:.1f}%)")
        print(f"停損洗出        ：{len(stopped)} 筆 ({len(stopped)/len(triggered)*100:.1f}%)")
        print(f"收盤未達目標    ：{len(closed)} 筆 ({len(closed)/len(triggered)*100:.1f}%)")
        print()

        # 勝率：分母=全部觸發（含收盤了結）
        wr_all = len(profitable) / len(triggered) * 100
        # 勝率：僅計「有明確停利或停損出場」者（排除純收盤了結的模糊地帶）
        resolved = hit_tp2 + tp1_then_breakeven + stopped
        wr_resolved = sum(1 for r in resolved if r["profit"]) / max(1, len(resolved)) * 100
        print(f"── 勝率 ──")
        print(f"獲利筆數：{len(profitable)}/{len(triggered)} = {wr_all:.1f}%   （分母=全部觸發）")
        print(f"獲利筆數：{sum(1 for r in resolved if r['profit'])}/{len(resolved)} = {wr_resolved:.1f}%   （分母=僅明確TP/SL出場）")
        print()

        # 達 TP1（半倉A成功鎖利）的筆數 = hit_tp2 + tp1_then_breakeven + tp1_then_close
        reached_tp1 = hit_tp2 + tp1_then_breakeven + tp1_then_close
        print(f"── 損益（元/股，毛）──")
        print(f"累積 PnL：{total_pnl:+.2f} 元/股")
        print(f"  → 達TP1+達TP2貢獻：{win_tp2:+.2f} 元/股")
        print(f"  → 達TP1(另一半保本平手)：{win_tp1_then_breakeven:+.2f} 元/股")
        print(f"  → 達TP1(另一半收盤)：{win_tp1_then_close:+.2f} 元/股")
        print(f"  → 停損虧損：{loss_stopped:+.2f} 元/股")
        print(f"  → 收盤了結：{close_pnl:+.2f} 元/股")
        print(f"平均每筆觸發 PnL：{total_pnl/len(triggered):+.2f} 元/股")

        # 盈亏比：平均獲利(達TP1的半倉A成功) / 平均虧損(停損)
        avg_win = sum(r["pnl"] for r in reached_tp1 if r["profit"]) / max(1, len([r for r in reached_tp1 if r["profit"]]))
        avg_loss = loss_stopped / max(1, len(stopped))
        print(f"平均獲利（達TP1且最終獲利）：{avg_win:+.2f} 元/股 | 平均虧損（停損）：{avg_loss:+.2f} 元/股")
        if avg_loss != 0:
            print(f"盈亏比（获利均/亏损均绝对值）：{abs(avg_win/avg_loss):.2f}")

    # ---- CSV ----
    os.makedirs(os.path.dirname(csv_out), exist_ok=True)
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["日期","次日","代號","名稱","分數","進場","停損","TP1","TP2",
                    "次日開","次日高","次日低","次日收","是否觸發","結果","PnL(元/股)"])
        for r in all_records:
            w.writerow([r["date"], r["next_date"], r["code"], r["name"], r["score"],
                        round(r["entry"], 2), round(r["sl"], 2), round(r["tp1"], 2), round(r["tp2"], 2),
                        r["o"], r["h"], r["l"], r["c"], r["triggered"],
                        r["outcome"] if r["triggered"] else "未觸發",
                        r.get("pnl", "")])
    print(f"\nCSV 已存：{csv_out}")

    # ---- TXT ----
    with open(txt_out, "w", encoding="utf-8") as f:
        f.write(f"【TP1半倉停利+拚TP2 回溯測試報告】2026 年 {month_label} 月（無滑點/手續費）\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"交易日數：{len(days)}\n全部入選筆數：{n_total}\n實際觸發進場：{len(triggered)} ({len(triggered)/max(1,n_total)*100:.0f}%)\n\n")
        if triggered:
            f.write(f"達TP1+達TP2：{len(hit_tp2)} 筆 | 達TP1(另一半保本平手)：{len(tp1_then_breakeven)} 筆 | ")
            f.write(f"達TP1(另一半收盤)：{len(tp1_then_close)} 筆 | 停損：{len(stopped)} 筆 | 收盤了結：{len(closed)} 筆\n")
            f.write(f"勝率(分母=全部觸發)：{wr_all:.1f}%\n")
            f.write(f"勝率(分母=僅明確TP/SL)：{wr_resolved:.1f}%\n")
            f.write(f"累積PnL：{total_pnl:+.2f} 元/股\n")
            f.write(f"平均每筆：{total_pnl/len(triggered):+.2f} 元/股\n")
    print(f"摘要已存：{txt_out}")


if __name__ == "__main__":
    main()

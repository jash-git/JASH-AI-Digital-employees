# -*- coding: utf-8 -*-
"""重算累積統計：凍結基底 CSV(cap=10-13) + 各實盤執行日 JSON(10-14~10-21)。
先驗證能重現既有總計，再纳入 10-21。JSON rows 用 pnl_gross/pnl_net；CSV 用中文欄位。"""
import csv, json, os

BASE = "/home/vblinux/daytrade_scanner/results"

def agg(rows):
    """rows: list of dicts with keys gross, net (float). All are triggered."""
    trig = len(rows)
    wins = sum(1 for r in rows if r["gross"] > 0)
    netwins = sum(1 for r in rows if r["net"] > 0)
    gross = sum(r["gross"] for r in rows)
    net = sum(r["net"] for r in rows)
    win_sum = sum(r["gross"] for r in rows if r["gross"] > 0)
    loss_sum = abs(sum(r["gross"] for r in rows if r["gross"] < 0))
    return dict(trig=trig, wins=wins, netwins=netwins, gross=gross, net=net,
               win_sum=win_sum, loss_sum=loss_sum)

def csv_to_rows(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("是否觸發") == "True":
                g = float(r["PnL(元/股,毛)"])
                n = float(r["PnL(元/股,扣費後)"])
                out.append({"gross": g, "net": n})
    return out

def json_to_rows(path):
    d = json.load(open(path, encoding="utf-8"))
    return [{"gross": r["pnl_gross"], "net": r["pnl_net"]} for r in d["rows"]]

# 1. 凍結基底 CSV (cap=10-13)
frozen = agg(csv_to_rows(f"{BASE}/backtest_tp1half_20260101~20261013.csv"))
print("凍結基底(cap=10-13):", {k: round(v,2) if isinstance(v,float) else v for k,v in frozen.items()})

# 2. 各實盤執行日 JSON
daily = ["20261014","20261015","20261016","20261019","20261020","20261021","20261022"]
day_agg = {}
for d in daily:
    path = f"{BASE}/verify_{d}_tp1half.json"
    if os.path.exists(path):
        day_agg[d] = agg(json_to_rows(path))
    else:
        print(f"(缺 {path})")

def combine(blocks, exclude=None):
    c = dict(trig=0,wins=0,netwins=0,gross=0.0,net=0.0,win_sum=0.0,loss_sum=0.0)
    for name, blk in [("frozen", frozen)] + list(blocks.items()):
        if exclude and name == exclude:
            continue
        for k in c:
            c[k] += blk[k]
    return c

pre = combine(day_agg, exclude="20261021")   # 不含 10-21（驗證既有總計）
print("\n【驗證：重現既有總計(至10-20)】")
lr_pre = pre['trig']-pre['wins']
print(f"觸發={pre['trig']} 毛={pre['gross']:+.2f} 淨={pre['net']:+.2f} "
      f"勝率={pre['wins']/pre['trig']*100:.1f}% ({pre['wins']}/{pre['trig']}) "
      f"勝勝率={pre['netwins']/pre['trig']*100:.1f}% ({pre['netwins']}/{pre['trig']})")
print(f"盈虧比={ (pre['win_sum']/pre['wins'])/(pre['loss_sum']/lr_pre):.2f} "
      f"(平均獲利{pre['win_sum']/pre['wins']:.2f} : 平均虧損{pre['loss_sum']/lr_pre:.2f})")

# 3. 纳入 10-21
post = combine(day_agg, exclude="20261021")
p1021 = day_agg["20261021"]
final = dict(trig=post['trig']+p1021['trig'], wins=post['wins']+p1021['wins'],
             netwins=post['netwins']+p1021['netwins'], gross=post['gross']+p1021['gross'],
             net=post['net']+p1021['net'], win_sum=post['win_sum']+p1021['win_sum'],
             loss_sum=post['loss_sum']+p1021['loss_sum'])

print("\n【10-21 單日(昨日10-20推薦→今日)】")
print(f"觸發={p1021['trig']} 毛={p1021['gross']:+.2f} 淨={p1021['net']:+.2f} "
      f"勝率={p1021['wins']/p1021['trig']*100:.1f}% ({p1021['wins']}勝{p1021['trig']-p1021['wins']}負)")

print("\n【更新後累積(至10-21)】")
lr = final['trig']-final['wins']
print(f"觸發={final['trig']} 毛={final['gross']:+.2f} 淨={final['net']:+.2f}")
print(f"勝率={final['wins']/final['trig']*100:.1f}% ({final['wins']}/{final['trig']})")
print(f"勝勝率={final['netwins']/final['trig']*100:.1f}% ({final['netwins']}/{final['trig']})")
print(f"盈虧比={(final['win_sum']/final['wins'])/(final['loss_sum']/lr):.2f} "
      f"(平均獲利{final['win_sum']/final['wins']:.2f} : 平均虧損{final['loss_sum']/lr:.2f})")
print(f"平均每筆毛={final['gross']/final['trig']:+.2f}")

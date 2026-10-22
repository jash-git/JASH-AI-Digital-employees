# 選股/回溯前的資料完整性檢查

比較 v1 vs v2 或做任何回溯前，先確認「選股日」在 feed 裡真有收盤。否則 v1/v2 會因各自日期解讀不同而比出假差異（見 SKILL.md 已知坑 #6、#7）。

## 為什麼「昨天沒有收盤」會發生
Yahoo 把台股日棒時間戳設在**開盤時（01:00 UTC = 09:00 CST）**。兩個後果：
- **cutoff 错位**：`cutoff=2026-10-12T00:00Z`（UTC 午夜）切在兩日之間，Yahoo `period2` 又放寬 → v1 抓到下一支棒（查 10-12 實際用到 10-13）。
- **切片回退**：v2 依日期字串 `<= "2026-10-12"` 切片，若 10-12 那支 close=None 被 parse_bars 跳過 → 最後一支有效棒掉回 10-08 或更早。

**判別凍結/假 feed 的黃金準則**：真實 live 行情不可能「昨天 close=None、今天卻有值」。若觀察到此逆反，代表連到的是一份凍結／部分灌入的資料（本環境即為此情況），不是選股邏輯有錯。

## 檢查腳本（跑完就知道該用哪天）
```python
import scanner as S
from collections import Counter
items = [(r.split(',')[0].strip(), '') for r in open('universe.csv', encoding='utf-8')
         if r.strip() and not r.startswith('#') and r.split(',')[0].strip().isdigit()]
last = []
for code, _ in items:
    _, rows = S.parse_bars(S.yahoo_chart(f'{code}.TW', rng='5y'))
    valid = [r for r in rows if r['close'] is not None]
    last.append(valid[-1]['date'] if valid else None)
print(Counter(last).most_common())   # 每檔「最後一支有效收盤日」的分佈
```
- 若所有檔都指向同一天（例如全 29 檔都是 2026-10-13）→ 那天就是本環境「最新已收盤完整交易日」，用它當選股日。
- 想確認某日是否全市場有效：把 `last` 換成「該日是否有非 None 收盤」的布林計數；全 0 表示該日 feed 未定案，不可回溯。

## 決策表
| 現象 | 解讀 | 處理 |
|---|---|---|
| 選股日每檔都有真收盤 | 正常，可直接比 v1/v2 | 用 slice_rows 對等切片後並跑 |
| 選股日全市場 close=None，但之後某天有值 | 該日 feed 未定案（凍結/假 feed） | 改用「之後第一支有效日」；別回溯該日 |
| v1/v2 用相同 --date 卻选出不同名單 | 日期错位（坑 #6），不是策略差 | 改用 compare_v1_v2.py 對等切片再比 |
| 昨天=None、今天有值 | 逆反 → 非 live 的凍結資料 | 以「最新有效日」為基準，並向使用者說明 |

## 輸出規範（沿用 SKILL.md）
同日 v1/v2 比較報告放 `results/報告_YYYYMMDD_v1_vs_v2.md`；原始對照可存 `results/compare_v1_v2_<date>.txt`。所有由本工具產生的報告一律放 `results/`，勿散落在專案根目錄。

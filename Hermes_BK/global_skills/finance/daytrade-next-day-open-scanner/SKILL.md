---
name: daytrade-next-day-open-scanner
description: Next-day-open day-trade scanner with entry, stop, target.
version: 1.0.0
tags: [finance, day-trade, taiwan-stock, scanner]
---

# 隔天開盤當沖選股掃描器（v1 + v2）

工具位置：`/home/vblinux/daytrade_scanner/`（亦連結至 `~/.hermes/tools/daytrade_scanner/`）

## 兩種版本，別搞混
| | **v1** `scanner.py` | **v2** `scanner_v2.py` |
|---|---|---|
| 技術面 | ✅ 成交量/均線/波段形態 | ✅ 完全相同（零修改） |
| 籌碼層 | ❌ 無 | ✅ T86 三大法人買賣超加分 |
| 做空估值 | ❌ | ✅ 外資大賣超時提供 |
| 即時選股 | `bash run.sh` / `python3 scanner.py` | `python3 scanner_v2.py --top 10 --min-score 45` |
| 回溯測試 | `backtest_sept2026.py --start-month N --end-month M` | `backtest_v2.py --start-month N --end-month M` |

日常選股用 v1 就夠。要籌碼面或做回溯才用 v2。

## 執行
```bash
cd /home/vblinux/daytrade_scanner
bash run.sh                 # v1: top12, min-score45，CSV → results/scan_YYYYMMDD.csv
bash run.sh --top 8         # 自訂筆數
python3 scanner.py --help   # 完整選項

python3 scanner_v2.py --top 10 --min-score 45     # v2: 含三大法人
python3 backtest_v2.py --start-month 1 --end-month 9   # v2 回溯（每週抓 T86）
```

## 設計原則（對應 Gemini 文章《隔天開盤當沖選股策略與技巧》bzX3xC5vGBXU）
四大金剛 → 自動化分級：
1. 成交量/流動性 ✅ Yahoo OHLCV 算量/5日均量 + 最小張數。
2. 籌碼集中度 ✅ **v2 已整合 T86**（三大法人買賣超，可回溯歷史日期）。外資持股前20名、融券僅最新快照或需人工。
3. 價量形態 ✅ 創波段新高、收/高比、站上MA20、多頭排列。
4. 消息面 ❌ 不適用結構化數據。

## 環境關鍵事實（重要）
- ✅ Yahoo Finance chart API (`v8/finance/chart/CODE.TW?range=3mo&interval=1d`) 可靠可批次。
- ✅ **T86** `twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json`：免 key、**可回溯歷史日期**（v2 籌碼層主力來源）。date 欄位格式 `'YYYYMMDD'`。
- ⚠️ **外資持股前20名** `openapi.twse.com.tw/v1/fund/MI_QFIIS_sort_20`：只給最新快照，無法回溯。
- ❌ **TWSE 官方 API** (`twse.com.tw/api/tw/s20,s23,s19,b465`、bfi82u)：回傳反爬 HTML / HTTP 403，本網域無法自動。三大法人買超排行、融券需人工查。
- ⚠️ HiStock/wantgoo/goodinfo DNS 解析失敗或需登入。
- Gemini share 連結（share.gemini.google）需 Google 登入，本環境讀不到。

## 評分：0-100，入選需 >=2 訊號且量放大
volume_surge(25) + breakout_newhigh(25) + strong_close_high(15) + ma_bullish_stack(15) + uptrend_above_ma20(10) + atr_liquidity(10).乖離>1.10 降級「觀望(開高走低風險)」。(scanner.py:66-67, DEFAULT_MIN_SCORE=45)

## 停損/停利（build_trade_plan，scanner.py:231）
- 進場 = 前日高；若當日已突破前日高 → 「收盤×1.003」追單。
- 停損 = max(價格0.8%, ATR*0.6)，上限 1.5%（THRESHOLDS in scanner.py:58-62）。
- TP1/TP2 = entry +/- risk × (1.5 / 2.5)，risk = entry - sl。

## v2 籌碼層邏輯（scanner_v2.py scan_one_v2）
- `scan_one_v2(code, name, cm, rows=None)`：rows 為預先切片歷史棒（回溯用），None → 抓全歷史（即時選股）。與 v1.scan_one(rows=...) 行為一致。
- 籌碼加分：外資買超 +15、投信買超 +10、外資前20大 +10，加在 v1 分數之上（總分上限 100）。
- ⚠️ **重要限制**：加分只在 stock「已達技術面門檻(score>=45)」後才作用。若技術面未過線就直接回 None，籌碼再好看也進不了清單 → 所以 v1/v2 回溯結果目前完全相同（見 results/v1_vs_v2_比較報告.md）。
- 若要讓籌碼真正影響入選：改「入選門檻」（如外資買超+score>=40）或「過濾」（剔除外資大賣超者），而非單純加分。

## 已知坑（本輪實測，別重犯）
1. **look-ahead bias**：v2 回溯若 scan_one_v2 不傳 rows=切片棒，它會內部抓全歷史 → 每天選都用到「最新價」而非當日收盤前。結果虛高。**修為傳 rows=切片棒**（scanner.py get_full_rows + slice_rows）。
2. **CSV 欄位為零**：scan_one_v2 算出 foreign_net 但沒存回 result dict → CSV「外資淨超(萬股)」全 0。修為加 `result["foreign_net"] = cs["foreign_net"]`、`investor_net`。
3. datetime.timezone.utc：import 要帶 timezone，別用 datetime.UTC。
4. Yahoo chart API 偶發 401/404 → 雙 host 容錯 + WARN 不中斷。
5. backtest_v2.py 抓 T86 用「每週一次」而非每日（每日 ~18000行 × 195交易日會超時）。T86 每日更新、無跳號，每週採樣不會漏任何交易日的可用資訊。

## 回溯結果基線（2026 1~9月）
v1 = v2：546入選 / 375觸發(69%) / 獲利45% / +604.8元淨利(扣成本) / base rate 50%。完整分析見 results/v1_vs_v2_比較報告.md。

## 文件
- README.md（開發者技術文件）、使用手冊.md（白話操作指南，含停損/停利範例、參考網址清單）。
- results/v1_vs_v2_比較報告.md、results/月度回溯報告_*.md、results/backtest_*_*.csv。
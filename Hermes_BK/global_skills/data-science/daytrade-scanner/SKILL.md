---
name: daytrade-scanner
description: "跑 daytrade scanner(v1/v2)選股：TWSE當日源+Yahoo歷史+健康檢查。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [daytrade, scanner, twse, yahoo, t86, data-source, backtest, Taiwan-stocks]
    category: data-science
---

# Daytrade Scanner（v1/v2）資料流程

## When to Use This
Use when running or improving the daytrade scanner at /home/vblinux/daytrade_scanner:
- 選股（當日）或回溯測試（backtest）v1/v2。
- 排查 Yahoo「當日未定案/None/逆轉」等資料問題。
- 評估或更換選股器的資料來源。
用 `screen_latest.py`（TWSE 權威當日 + 健康檢查）優於舊版 scan_on_date.py 的 UTC cutoff 法。

## 專案結構（/home/vblinux/daytrade_scanner）
- scanner.py = v1 純技術面（爆量+創新高+強勢收+均線排列，門檻 score>=45、至少2訊號、必爆量）。
- scanner_v2.py = v2 疊 T86 三大法人籌碼（加分制：外資買超+15/投信買超+10/持股前20+8；不改選股名單，只加分+給多空提示）。
- scan_on_date.py / scan_on_date_v2.py = 指定日期回溯（舊版，有 UTC cutoff 時區 bug）。
- data_source.py = TWSE 當日全市場日線 + 選股日決定 + 合併棒線（新）。
- screen_latest.py = 以 TWSE 權威當日為基準的 v1/v2 對等比較（含健康檢查，推薦用）。
- check_feed_gaps.py = 掃 Yahoo 資料缺口/未定案(None)/逆轉徵兆。
- backtest_sept2026.py = 月度回溯（--start-month/--end-month），含 simulate_trade() 當沖次日判定：進場觸發(h≥entry或o>entry)→停損→TP2→TP1→收盤，逐日對照下一根棒。
- backtest_tp1half_tp2.py = TP1先收一半、另一半拚TP2（A達TP1後B移到保本停損，故凡達TP1者皆贏）半倉停利回溯；無滑點/手續費。
- backtest_tp1_only.py / backtest_tp2_only.py = 全押單目標的對照組。
- backtest_v2.py = v2（+T86籌碼）回溯。
- compare_v1_v2_dated.py = 指定日期 v1/v2 對等回溯（同切片、可 --date/--top/--min-score），落 results/compare_dated_<D>.json。

## 資料來源（本環境已實測，2026-10）
✅ TWSE openapi `STOCK_DAY_ALL`：`https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL?date=YYYYMMDD`
   → 全市場(~1378檔,含ETF)当日 OHLCV JSON。權威、已定案。⚠ date 參數在本環境被忽略，固定回「最新已定案交易日」，只適合當日選股不能抓歷史。
✅ Yahoo Finance chart API：`https://{query1|query2}.finance.yahoo.com/v8/finance/chart/{code}.TW`
   → 唯一能抓多日歷史的來源（MA20/ATR14/創新高40 需要歷史）。回溯靠它。
✅ TWSE RWD `T86`：`https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json`
   → 三大法人買賣超（v2 籌碼層用）。可回溯。⚠ 當日可能 0 檔（隔日才出），首跑 0 檔稍後重跑或隔日即可。
⚠ TWSE openapi 其他端點：路徑要對，正確是 `/v1/exchangeReport/...`、`/v1/fund/...`。打錯回 404 頁（非被擋）。
❌ wdata.tw：DNS 解析失敗。❌ Stooq：JS proof-of-work bot wall。⚠ TPEx 行情端點本環境回 404，且 universe 台股交所主板用不到。

## 核心做法：A→B 資料備援 + settlement ceiling（Yahoo 主源、TWSE 備援）
v1/v2 指標需多日歷史，TWSE 只給當天。screen_latest.py / compare_v1_v2_dated.py / data_source.py 的做法：
1. `collect_yahoo_full()` 每檔抓 Yahoo 5y 歷史一次（主源 A）。`resolve_screen_date_union()` 取兩源全覆蓋最晚日為 D，但**不超過 TWSE 權威已定案日（settlement ceiling）**——避免用到未定案的當日線（look-ahead）。
2. `gather_rows_union()` = Yahoo(<=D) + TWSE 填補 D 当天 Yahoo 缺的棒（備援 B）。TWSE 只在 Yahoo 缺棒時補位，不延伸 D。
3. 守衛：兩源在 target date 都無有效收盤 → 「缺資料」停跑、不產出報告。
4. v1.scan_one(rows) 與 v2.scan_one_v2(rows, cm) 用同一批資料 → 對等比較（結果與 compare --date <D> 完全一致）。

## 必記坑（Gotchas）
- ⚠ 當沖回溯的 next-bar 只能用「已定案」行情：Yahoo 會先帶入未收盤的「今日」棒。`backtest_tp1half_tp2.py` 以 TWSE 已定案日為 cap 排除之；預設自動跑到最新已定案日，當 Yahoo 尚未釋出中間已定案棒時（如只跳到今日 partial）該段會自然跳過，等釋出後自動補進。
- ⚠ UTC cutoff 時區 bug：scan_on_date.py 用 cutoff=目標日T00:00Z。台股日棒時間戳 01:00UTC=09:00CST，午夜 UTC 切到兩日之間、Yahoo period2 又放寬 → v1 實際抓到「次日」棒。回溯請用 screen_latest 的日期字串 <=D 切片法或傳切片 rows。
- ⚠ look-ahead：scan_one_v2(code,name,cm,rows=None) 若 rows=None 會重抓全歷史用到未來價。回溯必傳切片好的 rows。
- ✅ v2 籌碼分顯示修正：compare_v1_v2_dated.py 的「差異對照」原用 `V2分−V1分`（分數差），當 V2 達 100 上限會低估真實籌碼加分（如遠傳 85+25=110→100，顯示成 +15）。已改為讀 `chumma_boost` 欄位（scanner_v2 恒有）。screen_latest 一直用 chumma_boost，故兩者此前差 +10。
- ✅ 策略A/B（突破vs拉回）：build_trade_plan 依 breakout_new_high 定進場價（A=前日高、B=收盤+0.3%）。它只透過「進場價」影響當沖回溯 PnL（entry/sl/tp1/tp2 本就用在 backtest_tp1half_tp2），不是獨立變因；screen_latest 與 compare 共用同一 scan_one，處理一致。報告顯示該標籤只是 metadata，不另改統計。
- ✅ A→B 資料備援 + 守衛（compare / screen_latest 共用 data_source 輔助函式）：A=Yahoo 主源，B=TWSE STOCK_DAY_ALL 備援。`gather_rows_union()` = Yahoo(<=D) + TWSE 填補 D 当天 Yahoo 缺的棒；`resolve_screen_date_union()` 取兩源全覆蓋最晚日為 D，但**不超過 TWSE 權威已定案日（settlement ceiling）**——避免用到未定案的當日線（look-ahead）。守衛：兩源在 target date 都無有效收盤 → 印「缺資料」並停跑、不產出報告；只要有任一源有正確資料就產生對應文件。`collect_yahoo_full()` 用 rng=5y（與 compare 原始一致；1y 会掉臨界股）。
- ✅ 驗證（2026-10-13）：TWSE 停在 10/12、Yahoo 有 10/13 → fallback 正確解析到今日實際交易日；T86 當日籌碼也已釋出，無日期錯位。
- v2 加分制：只加不減，名單與 v1 相同；外資大賣超只做「看空風險」提示不剔除。要讓籌碼真正影響選股得改邏輯（當門檻/剔除/加權）。
- 比較 v1/v2 一定要對等資料日期，否則因日期错位得出假差異。
- ⚠ 回溯數字會漂移：Yahoo 歷史棒會被後修，同一段期間每次重跑的入選筆數/勝率/獲利可能不同。把回測結果當「相對參考」而非固定事實；比較兩種規則時要用同一套資料抓取點才公平。

## 常用命令
- 當日最新對等選股（screen_latest）：`python3 screen_latest.py [--top 15] [--min-score 45]` → results/screen_v{1,2}_<D>.csv。**已對齊 compare_v1_v2_dated 的切片基底**（純 Yahoo、按日期字串 <=D 公平切片；自動決定 D = 兩源全覆蓋最晚日但不超 TWSE 已定案天花板）。實測與 `compare_v1_v2_dated.py --date <D>` 結果完全相同（V1+V2 全部一致），兩者可互用。
- **官方/一致性選股報告**：用 `python3 compare_v1_v2_dated.py --date <最新已定案日>` → results/compare_dated_<YYYYMMDD>.json，再依 results/選股報告_YYYY-MM-DD_v1_vs_v2.md 模板寫。**所有「選股報告_...」都用此法**（Yahoo 日期字串切片 ≤D、公平切片、無 look-ahead），保證日與日可比。
- 指定日期回溯 v1：`python3 scan_on_date.py --date 2026-10-12`
- 指定日期回溯 v2：`python3 scan_on_date_v2.py --date 2026-10-12`
- 掃 Yahoo 缺口：`python3 check_feed_gaps.py`
- 【當沖績效回溯】TP1半倉停利+另一半拚TP2（無滑點）：`python3 backtest_tp1half_tp2.py`
  - 預設自動跑「1月 → TWSE最新已定案日」——每次跑都自动纳入迄今所有已 settled 的資料（如 10 月至今），不用手動改月份。
  - `--end-month 9` = 固定月份回溯；`--end-date 2026-10-10` = 指定截止日。next-bar 以 TWSE 已定案日為 cap，排除 Yahoo 未定案「今日」棒（防 look-ahead）。
  - Jan–Sep 2026：勝率 61.7%、累積毛 PnL +2556 元/股、盈亏比 2.31。同窗口單目標對照：TP1-only 46%/+701、TP2-only 44%/+1583 → 半倉制在勝率與總獲利兩項都最強。
  - **預設已扣當沖「法定/監管最高費」**（買0.1615%、賣0.4615%），輸出同時給毛額與扣費後淨利。1~10-12：毛 +2,550 / 淨 +1,036 元/股、淨勝率 56.2%（費吃掉約59%，主要在高價股如大立光）。實際當沖多數券商免手續費，真實净利更高。
- 半倉停利回溯（TP1收一半+另一半拚TP2，A賣後B保本）：`python3 backtest_tp1half_tp2.py --start-month 1 --end-month 9` → results/backtest_tp1half_01~09_{csv,summary.txt}
- 指定日期 v1/v2 對等回溯：`python3 compare_v1_v2_dated.py --date 2026-10-12` → results/compare_dated_20261012.json
- 備份：用 `sudo /home/vblinux/Hermes_BK/backup.sh`（自動 sudo，整份拷貝 daytrade_scanner→Hermes_BK/Code/，並刷新所有 profile/skill/memory）。**不要手搓 tar 快照**——backup.sh 已含整個專案（見 project-backup skill）。改 universe.csv 前跑一次即可。

## 提高準確性/穩定度（優先序）
1. 資料源：當日用 TWSE STOCK_DAY_ALL，歷史留 Yahoo。選股前先健康檢查，有未定案/逆轉就停。
2. 正確性：回溯用日期字串切片 + 真休市日曆（TWSE `/holidaySchedule/holidaySchedule`），別用工作日近似。
3. 驗證：定期用 backtest_tp1half_tp2.py 實測勝率/毛利/盈亏比/回撤，作為規則優劣的相對參考（無滑點/手續費）。⚠ 回測數字會因 Yahoo 歷史棒後修而漂移——當相對基準、勿當固定事實。
4. 風險：單筆風險上限、波動率調整部位、連續停損縮手。
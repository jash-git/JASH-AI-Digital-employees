---
name: daytrade-scanner
description: "跑 daytrade scanner(v1/v2)選股：TWSE當日源+Yahoo歷史+健康檢查。"
version: 1.1.0
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

## 核心做法：A→B 資料備援 + A-first 選股日（Yahoo 主源、TWSE 備援）
v1/v2 指標需多日歷史，TWSE 只給當天。screen_latest.py / compare_v1_v2_dated.py / data_source.py 的做法：
1. `collect_yahoo_full()` 每檔抓 Yahoo 5y 歷史一次（主源 A）。選股日 D = **A（Yahoo）已定案的最晚交易日**；TWSE（B）落後不降級 D，只在 Yahoo 缺棒時補位。`resolve_screen_date_a_first()`（守衛 `_is_day_settled`）的過收盤判定 只挡「未定案的當日線」（盘中/收盤剛過的 partial OHLC，避免 look-ahead），**不**因 TWSE 端點落後就把 D 往下退——只要 A 有完整已定案日線就用 A（符合『A 有資料就用 A；兩源都沒資料才不產報告』）。
2. `gather_rows_union()` = Yahoo(<=D) + TWSE 填補 D 当天 Yahoo 缺的棒（備援 B）。TWSE 只在 Yahoo 缺棒時補位，不延伸 D。
3. 守衛：兩源在 target date 都無有效收盤 → 「缺資料」停跑、不產出報告。
4. v1.scan_one(rows) 與 v2.scan_one_v2(rows, cm) 用同一批資料 → 對等比較（結果與 compare --date <D> 完全一致）。

## 必記坑（Gotchas）
- ⚠ 當沖回溯的 next-bar 只能用「已定案」行情：Yahoo 會先帶入未收盤的「今日」棒。`backtest_tp1half_tp2.py` 以 TWSE 已定案日為 cap 排除之；預設自動跑到最新已定案日，當 Yahoo 尚未釋出中間已定案棒時（如只跳到今日 partial）該段會自然跳過，等釋出後自動補進。
- ⚠ UTC cutoff 時區 bug：scan_on_date.py 用 cutoff=目標日T00:00Z。台股日棒時間戳 01:00UTC=09:00CST，午夜 UTC 切到兩日之間、Yahoo period2 又放寬 → v1 實際抓到「次日」棒。回溯請用 screen_latest 的日期字串 <=D 切片法或傳切片 rows。
- ⚠ look-ahead：scan_one_v2(code,name,cm,rows=None) 若 rows=None 會重抓全歷史用到未來價。回溯必傳切片好的 rows。
- ⚠ **今日選股日 D = A（Yahoo）已定案最晚日，TWSE 落後不降級**：跑「今天的選股」只要 Yahoo 有完整當日線（收盤後即為已定案），D 就用它；TWSE `STOCK_DAY_ALL` 在本環境 date 參數被忽略、常落後一天，**不能**因此把 D 往下退成昨天。只有兩源在該日都無有效收盤才不產報告（守衛）。**screen_latest.py 現已 A-first**（`resolve_screen_date_a_first`，過收盤才取当日、盘中用昨日定案日），可直接跑今日選股；`compare_v1_v2_dated.py --date <D>` 則用於固定日期回溯/一致性報告（指定任意過去日、無天花板）。兩者對等、結果相同。
- ✅ v2 籌碼分顯示修正：「差異對照」若用 `V2分−V1分`（分數差）會因 100 上限低估真實籌碼加分，**必須讀 `chumma_boost` 欄位**（scanner_v2 恒有）。兩種失真都要防：(a) V1<100 但 V2 撞線（如 85+25=110→100，顯示 +15、實 +25）；(b) **V1 本身已 100**（如遠傳 100+25 撞線），顯示「100→100」差 0，但 `chumma_boost`=+25——看起來像沒加分，實際有。screen_latest 一直用 chumma_boost，故總和與單檔加分都按真實值報（實測 V1 均分 70.0、V2 顯示均分 83.75、籌碼真實和 +145）。
- ✅ 策略A/B（突破vs拉回）：build_trade_plan 依 breakout_new_high 定進場價（A=前日高、B=收盤+0.3%）。它只透過「進場價」影響當沖回溯 PnL（entry/sl/tp1/tp2 本就用在 backtest_tp1half_tp2），不是獨立變因；screen_latest 與 compare 共用同一 scan_one，處理一致。報告顯示該標籤只是 metadata，不另改統計。
- ✅ A→B 資料備援 + 守衛（compare / screen_latest 共用 data_source 輔助函式）：A=Yahoo 主源，B=TWSE STOCK_DAY_ALL 備援。`gather_rows_union()` = Yahoo(<=D) + TWSE 填補 D 当天 Yahoo 缺的棒；選股日 D = A（Yahoo）已定案最晚日（A-first，TWSE 落後不降級；D 決定見核心做法第 1 點），守衛(_is_day_settled) 只挡未定案當日線（look-ahead）。守衛：兩源在 target date 都無有效收盤 → 印「缺資料」並停跑、不產出報告；只要有任一源有正確資料就產生對應文件。`collect_yahoo_full()` 用 rng=5y（與 compare 原始一致；1y 会掉臨界股）。
- ✅ 驗證（2026-10-13）：TWSE 停在 10/12、Yahoo 有 10/13 → fallback 正確解析到今日實際交易日；T86 當日籌碼也已釋出，無日期錯位。
- v2 加分制：只加不減，名單與 v1 相同；外資大賣超只做「看空風險」提示不剔除。要讓籌碼真正影響選股得改邏輯（當門檻/剔除/加權）。
- 比較 v1/v2 一定要對等資料日期，否則因日期错位得出假差異。
- ⚠ 回溯數字會漂移：Yahoo 歷史棒會被後修，同一段期間每次重跑的入選筆數/勝率/獲利可能不同。把回測結果當「相對參考」而非固定事實；比較兩種規則時要用同一套資料抓取點才公平。
- ⚠ **改中文報告用 ASCII anchor + regex**：`patch` 工具與 Python `str.replace` 都容易在繁體中文字符上 byte mismatch（手打的 CJK 與檔案內 bytes 不一致 → 0 match）。要改滿是中文的 md，用 ASCII 錨點 + `[^\n]*?`/`.*?` 通配跳過中文區（例如匹配 `1~10-12` 到 `56.2%` 之間的整句，中段中文用通配帶過），再對匹配結果只做數字 replace；或先 `read_file` 取原文確認字元再換。**用 `str.replace` 時每處斷言 `count==1`（≠1 就停手檢查，勿 blindly replace_all）；整行 CJK 难吻合時，改按行號讀入、只替換行內 ASCII 數字/日期 token（如 +2,569.27→+2,568.52），避開整段中文。**

## 報告撰寫與實盤驗證（檔案分工）

本專案的「績效主報告」與「每日實盤驗證」有固定分工，寫/更新報告時遵守：

1. **主報告只放「跑動統計總數」**：`報告_TP1半倉拚TP2_2026.md` 這類主報告只承載累積統計（入選/觸發/勝率/累積毛·淨 PnL），隨已定案日延伸。**不要**把每日逐檔明细塞進主報告。
2. **每日完整分析另存 dated 檔案**：每天的實盤驗證寫成 `results/驗證_YYYY-MMDD_選股執行結果.md`，格式沿用既有 `驗證_2026-10-13_選股執行結果.md`（判定規則→逐檔表+每檔敘述→總結果→誠實解讀→結論→附錄）。主報告「延伸至今日」小節只列總數並指回該 dated 檔案。
3. **統計要「統計在一起」**：新資料要併進既有的「延伸至今日」（section 五）那張表，**不要**另開一個平行小節重複同樣的總數（會把同一套數字拆成兩份）。headline 數字同步更新到 section 一、費用解讀放 section 六。
4. **回溯 vs 今日實盤是「互不重疊」直接加總**：`backtest_tp1half_tp2.py` 的 next-bar cap = TWSE 已定案日，抓不到尚未 settled 的「今日」棒；昨日推薦 → 今日實際成交正是回溯尚未涵蓋的那一段（D=選股日 → 下一根實際棒）。用同一套 `evaluate()` 判定後加總即「完整至今統計」。加總前**先確認無重疊**：檢查新 CSV 的 screen_date 是否已含該日（若已含＝已被回溯收掉，勿重複加）；TWSE 釋出該日後，重跑回溯會自然把當日收進窗口。
5. **更新累積數字時，區分「現況 headline」與「歷史敘述」**：只有承載「至今累積」的 headline table（section 一）、表格總計行、淨利勾稽行要換成新數；描述「某執行日區塊當時效果」的過去式條目（例：「…把累積毛從 +2,579.62 拉到 +2,569.27、勝勝率 55.8%」**保留當時數字**不要改——它記錄該區塊當下的累積端點）。全篇「N實盤執行／實盤區塊」計數要一致同步（新增一日 → N→N+1），但此同步只動承載累積的 headline，不动歷史敘述行內的舊總數。換完用 `grep -c` 查舊數字剩餘處數是否符合預期（現況數字應為 0、純歷史敘述可留 1）。
### 批量更新彙總報告的編輯手法（每日驗證後必做）

主報告 `報告_TP1半倉拚TP2_2026.md` 一次要換十幾個位置（section 一表格、section 五總計行、淨利勾稽行、當日條目）。不要逐處呼叫 `patch`——多筆對**同一檔**的 patch/str.replace **並發會競寫**，且單筆無效替換會**靜默成功**（pattern 沒匹配也不報錯），以為換了其實舊數字還在。用「整檔讀入 → 依行號逐行 ASCII 正則替換 → 一次寫回」：

1. `lines = open(path, encoding='utf-8').readlines()`（保留每行 `\n`），之後一律以 **1-indexed 行位置**定位。⚠ **插入新表格行/條後所有行號會整體位移**——插入要麼由下往上做、要麼做完重新 `grep -n` 按內容確認，別信舊行號（用舊 sed 行號會抓到移位前的無關行）。
2. 每行用 `re.sub` 只動 **ASCII token**（數字、`%`、日期），pattern 的**空白要與檔案內完全一致**（漏掉 `2.15` 與 `=` 之間的空格就無匹配而靜默失敗）；整段 CJK 照既有「ASCII 錨點 + 通配」原則跳過，勿手打。
3. 每處替換都 `assert new != line`（自訂 helper）——這是無效匹配的最后一道防線，沒斷言就把舊數字當新數留下。
4. 全部改完最後 `f.writelines(lines)` **一次寫回**（原子、不中途競寫）。
5. 換完依第 5 點區分「現況 headline」與「歷史敘述」，再 `grep -c` 核舊現況數字應為 0。

**驗證工具資料也要跟**：新增 `verify_<YYYYMMDD>_tp1half.json` 後，若要用 `results/recompute_cumulative.py` 重算累積總數，要把該日期加進它的 `daily = [...]` 清單。漏掉時腳本照常跑完、數字看起來對，但「重現」的是少含最新一日的過期累積（假正確）；新增執行日後先 `grep -n <YYYYMMDD>` 確認日期已在清單內。**主報告累積數字是手動換的、不依賴此清單**——這步只保驗證工具不失真。

## 常用命令
**- 當日最新對等選股（screen_latest）：`python3 screen_latest.py [--top 15] [--min-score 45]` → results/screen_v{1,2}_<D>.csv。**已對齊 compare_v1_v2_dated 的切片基底**（純 Yahoo、按日期字串 <=D 公平切片）。自動決定 D = **A（Yahoo）已定案的最晚交易日**（A-first，過收盤≥13:30 CST 才取当日；盘中回退至最近定案日），TWSE 落後不降級 D。實測與 `compare_v1_v2_dated.py --date <D>` 結果完全相同（V1+V2 全部一致），两者可互用。
- **官方/一致性選股報告**：用 `python3 compare_v1_v2_dated.py --date <最新已定案日>` → results/compare_dated_<YYYYMMDD>.json，再依 results/選股報告_YYYY-MM-DD_v1_vs_v2.md 模板寫。**所有「選股報告_...」都用此法**（Yahoo 日期字串切片 ≤D、公平切片、無 look-ahead），保證日與日可比。
- **回應「跑 [某日] 選股 + v1/v2 差多少 + 寫完整報告」**（常見每日指令）：這是**選股報告 class**（當日 v1/v2 入選對比），不是實盤驗證。① 先定 D = 該日的已定案交易日（「昨天」= 昨日；若今日未收盤或 TWSE 落後，`screen_latest.py` 會自動退到最近定案日）。② `python3 compare_v1_v2_dated.py --date <D>` → results/compare_dated_<D>.json（對等 JSON，與 screen_latest 完全一致）。③ 依**最接近的既有 `選股報告_<prev>_v1_vs_v2.md`** 當格式錨點，寫入 `results/選股報告_<D>_v1_vs_v2.md`。⚠ **別跟 `驗證_<YYYY-MMDD>_選股執行結果.md` 搞混**：後者是「D-1 推薦、D 實際成交」的 TP1半倉拚TP2 逐檔驗證（用 `backtest_tp1half_tp2.py::evaluate()`），與本 class 是兩份不同 dated 檔案；兩者日期都落在 D 附近，寫前讀一下確認目標檔案，才不會重疊或漏寫。
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
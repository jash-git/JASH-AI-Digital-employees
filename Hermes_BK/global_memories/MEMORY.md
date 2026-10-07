Playwright single-arrow-function-arg wrapping quirk: when calling page.evaluate("(arg) => {...}", {"arg": value}) with a SINGLE arrow function argument, Playwright wraps the arg as an object — inside the callback `arg` becomes `{arg: value}`, so `arg.y` is undefined. Fix: either destructure in JS `(arg) => { const {y} = arg; ...}` or pass a plain numeric/string literal embedded via Python `%f`/string formatting (no arg passing). Verified while QA-testing /home/vblinux/zuma.html.
§
Long-running downloads in terminal() get KILLED when the foreground call times out at 420s (process-group kill). Fix: double-fork daemonize so it survives — os.fork()>0 → _exit(0); os.setsid(); os.fork()>0 → _exit(0); then dup fds to log file. Verified working for missav HLS download (survived multiple separate terminal polls). Alternative: use terminal(background=true) which tracks the process itself.
§
Daytrade scanner project (/home/vblinux/daytrade_scanner/): v1 = scanner.py 純技術面選股（DEFAULT_MIN_SCORE=45，入選門檻）；v2 = scanner_v2.py 在 v1 之上疊加 T86 三大法人籌碼層。T86 (twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL) 可歷史回溯逐檔三大法人買賣超（到2019+）；openapi.twse.com.tw/v1 端點只有最新快照（?date=被忽略）。
§
v2 回溯 look-ahead bug：scanner_v2.scan_one_v2(code,name,cm,rows=None) 若 rows=None 會重新抓全歷史 Yahoo → 用到未來價。回溯必須傳入切片好的 rows（backtest_v2.py 用 slice_rows(rows,target_date)）。修好後 v1 與 v2 在 1~9月回溯結果完全相同：546入選/375觸發(69%)/獲利45%/毛利+1542/淨利+604.8。
§
原因（重要）：v2 籌碼層是「加分制」——只在 stock 已達技術面門檻(score≥45)之後才加 chumma_boost(外資買超+10/投信買超+10)，從未把低分股拉進清單。所以選股名單不變、結果一致。要讓籌碼真正影響選股得改邏輯：把籌碼當入選門檻 / 過濾達標股剔除外資大賣超 / 放大加權。比較文件：results/v1_vs_v2_比較報告.md。
§
daytrade_scanner 備份路徑（專案 /home/vblinux/daytrade_scanner）：(1) 原始錯誤版 universe.csv（30行、名稱全錯）保留於 /home/vblinux/Hermes_BK/Code/daytrade_scanner/universe.csv（10/3建立，root所有）。(2) 修正後完整專案壓縮備份在 /home/vblinux/Hermes_BK/daytrade_scanner_bk/daytrade_scanner_<timestamp>.tar.gz。universe.csv 已用 T86 官方中文名重校為 29檔（移除查無代號金鼎證）。改 universe 前先 tar czf 備份再動。
§
T86 三大法人籌碼資料時效（twse.com.tw/rwd/zh/fund/T86）：scan_on_date_v2.py 首次跑可能抓到「有法人資料的標的：0 檔」（當日數據尚未釋出），稍後重跑或隔天才補齊。實測 2026-10-06：首跑 0 檔 → 重跑 18820 檔，且顯示兩檔外資大賣超（鴻海 -1998萬股、聯發科 -391萬股）→ v2 標「看空風險」，隔日(10/07)兩檔果然低開破損。v1/v2 差 0 時要先確認是「籌碼中性」還是「資料未出」，別誤判；v2 加分制只加不減、賣超只做提示不剔除達標股。
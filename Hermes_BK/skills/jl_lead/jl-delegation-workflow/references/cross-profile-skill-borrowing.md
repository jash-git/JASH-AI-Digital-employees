# 跨 Profile Skill 借鏡方法論（2026-09-22 建立）

## 何時用這份文件
當你要審查另一個 profile 的 skill（例如 vpos_lead、jl_php），判斷「有哪些值得整合進 jl-delegation-workflow」時，照此流程做。目標是**挑出跨領域通用的委派/QA/監控缺陷**，而非逐字複製。

## 核心篩選原則：通用 vs 語言專屬

### ✅ 值得借鏡（與語言/框架無關）
這些是「多檔案委派 + Cron 監控 + QA 閉環」的結構性缺陷，任何技術棧都成立：
- watchdog 漏建 / 重派漏建 / 收尾對帳（orphan detection）
- dev→qa 並行造成的 race condition（stale file → 假陽性 REJECTED）
- QA 完成審查卻不寫報告檔（verdict JSON ≠ 交付物）
- cascade/多檔案任務的「管窺效應」（子代理只處理派單清單、未全目錄掃描）
- sibling subagent 並發改 task_board.json → patch fuzzy matching 失準
- CRLF↔LF cosmetic diff 被當成實質錯誤（越修越糟）
- task_board.json 更新後沒做 JSON 驗證 + 備份

### ❌ 刻意不搬（語言/框架專屬）
C# / Avalonia 專屬陷阱與 PHP/Layui 無關，搬了只會汙染規範：
- CS0122 / CS0103 / CS0136 / CS1656 等編譯錯誤
- System.Drawing → ImageSharp migration
- proxy property cleanup、extract-static-to-singleton
- m_XXX → mXxx 命名慣例
- HttpClientFactory pooling、DllImport extraction、connection pooling（SQLite 語境）
- JSON serialization（WhenWritingNull vs NullStringToEmptyConverter）

**判斷準則**：如果該條教訓的「根因」依賴某個特定語言/框架/編譯器的行為，它就是專屬的，不搬。如果根因是「流程結構」「工具誤用」「認知偏差」，那就是通用的，借鏡。

## 工具移植：複製 vs 改良（關鍵決策）

**不要盲目 `cp` 別人的 script**。先問三件事：
1. **它的 cache/輸入結構跟我一樣嗎？** — vpos 的 `monitor_subagent.py` 讀「單檔 transcript」，靠猜內容找 `final_response/completed`。jl_lead 的 delegation cache 是 `manifest.json + task-N.log`，manifest 直接給權威 `status/completed/exit_reason`。
2. **改良後是否更準？** — jl_lead 結構下，先讀 manifest（權威）比解析 log 內容猜狀態更可靠；log tail 留作「卡死偵測」（停更 >10 分鐘）的備用訊號。
3. **路徑/profile 硬編碼要換嗎？** — vpos 腳本硬編碼 `.../profiles/vpos_lead/cache/delegation/live`，移植必須改成 jl_lead 的路徑。

**結論**：vpos 的 monitor_subagent.py 是「猜測式」（單檔、解析內容），jl 版改寫成「權威優先」（manifest.json 給 status + log tail 偵測 stuck）。這是**改良而非複製**——因為輸入結構不同。若兩 profile 結構完全一致，才是直接 cp + 換路徑。

## jl_lead delegation cache 結構（移植時必記）
```
~/.hermes/profiles/jl_lead/cache/delegation/
├── live/<delegation_id>/
│   ├── manifest.json     # 權威：status / completed / exit_reason / tasks[].log
│   └── task-N.log        # 完整對話 log（卡死偵測用：看最後修改時間 + tail）
└── subagent-summary-*.txt
```
- `manifest.json` 的 `tasks[0].status` = completed/failed/running，`exit_reason` = completed/error/interrupted。
- task-N.log 的最後修改時間用於「log 停更 >10 分鐘 = stuck」偵測（manifest 為 running 或不存在時尤其重要）。
- **注意**：live/ 下累積的是歷史 transcript（可能數十個），即時狀態仍以 `cronjob_manage list` + `delegate_task list` 為準。本工具是「輔助診斷」（讀出停在哪、log tail 是什麼），不取代權威來源。

## 執行流程（審查另一個 profile skill 時）
1. **完整讀取**對方的 SKILL.md（用 read_file，注意結尾可能被截斷；若被截斷先確認 DoD/收尾段是否齊全）。
2. **比對**自己現有 skill，找出「對方有、我沒有」的通用缺陷。
3. **逐項過濾**：通用 → 借鏡；專屬 → 跳過（記錄原因，不搬）。
4. **工具類**：先確認輸入結構是否一致，決定 cp vs 改良。改良後用真實 transcript 實測（單一已知 completed + `--all` 列出全部），確認判讀正確再入库。
5. **同步 + 備份**：patch 自己的 SKILL.md → 複製到 global + 各下屬 profile（md5 全驗）→ Hermes_BK 備份。

## 實務提醒
- terminal 攔截：含中文正則的 `grep -cE '陷阱17'` 這類指令可能觸發 hardline blocklist。改用純 `cp` + `md5sum`，或 `read_file` 確認內容。
- skill 是「profile 複製、非 symlink」：在 lead 新增/修改 skill **不會**自動出現在下屬。必須手動 `cp` 到 global + jl_php/jl_ui/jl_qa，並用 md5sum 驗證五份一致。
- vpos 的 SKILL.md 結尾曾有 DoD 段落被截斷（972→970 行後補齊）。審查時若發現對方文件結尾不完整，先指出、別假設內容。

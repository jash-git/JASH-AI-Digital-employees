# 跨 Profile Skill 借鏡方法論（2026-09-22 建立，借鏡 jl_lead cross-profile-skill-borrowing.md）

## 何時用這份文件
當你要審查另一個 profile 的 skill（例如 jl_lead、jl_php），判斷「有哪些值得整合進 vpos-delegation-workflow」時，照此流程做。目標是**挑出跨領域通用的委派/QA/監控缺陷**，而非逐字複製。

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
- Gateway 常駐韌性四項檢查（is-active / Linger / enabled / process PID）

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
1. **它的 cache/輸入結構跟我一樣嗎？** — 確認 delegation cache 的 manifest.json + task-N.log 結構一致。vpos_lead 與 jl_lead 的 live transcript 都是「manifest.json + task-N.log」，manifest 直接給權威 status/completed/exit_reason。
2. **改良後是否更準？** — 先讀 manifest（權威）比解析 log 內容猜狀態更可靠；log tail 留作「卡死偵測」（停更 >10 分鐘）的備用訊號。
3. **路徑/profile 硬編碼要換嗎？** — 移植必須把硬編碼路徑改成目標 profile（如 `.../profiles/vpos_lead/cache/delegation/live`）。

**結論**：若兩個 profile 的 delegation cache 結構完全一致，才是直接 cp + 換路徑；結構不同則改良後再用真實 transcript 實測。

## vpos_lead delegation cache 結構（移植時必記）
```
~/.hermes/profiles/vpos_lead/cache/delegation/
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
- skill 是「profile 複製、非 symlink」：在 lead 新增/修改 skill **不會**自動出現在下屬。必須手動 `cp` 到 global + vpos_core/vpos_ui/vpos_qa，並用 md5sum 驗證一致。
- 審查時若發現對方文件結尾不完整（DoD 段落被截斷），先指出、別假設內容。

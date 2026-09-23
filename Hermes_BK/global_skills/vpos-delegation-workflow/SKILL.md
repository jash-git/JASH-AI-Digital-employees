---
name: vpos-delegation-workflow
description: VPOS Avalonia 專案任務委派、監控與 QA 閉環標準作業程序
---

# VPOS Project Delegation Workflow

## 核心原則
1. **全面下放**: 除最終編譯打包外，所有開發與審查任務必須委派給對應下屬 (`vpos_core`, `vpos_ui`, `vpos_qa`)。
2. **強制監控**: 委派任務後，**必須**立即建立 Cron 排程（每 3 分鐘檢查），repeat 依任務規模動態調整：簡單修復(≤5處)→3, 中等(5~20)→6, 大型重構(>20)→10。
3. **閉環審查**: 下屬完成後，必須指派 `vpos_qa` 進行程式碼審查，未通過 QA 不得進入下一問題。
4. **QA PASS 後通知使用者驗收 (鐵律)**: 無論誰執行 QA（vpos_qa delegate_task、hermes chat、或 vpos_lead 手動 grep），只要任務狀態轉為 DONE + qa_review="PASS"，**必須立即通知使用者進行編譯驗收**。
5. **待命模式**: 通知使用者後進入待命狀態。在下達「繼續下一個」指令前，不主動派發新任務、不更新 task_board.json（除非必要）。等待使用者明確指示才繼續。
6. **Graphify 優先 (2026-08-19 新增)**: 分析任務時必須優先使用 graphify 查詢依賴關係，grep 僅用於最終驗證。
7. **子代理主動回報 (2026-08-19 新增)**: dispatch 後 5 分鐘內必須主動檢查子代理狀態，不可等待 Cron。Cron 是防呆機制，不是主要溝通管道。
8. **同時下屬不超過 2 個（鐵則, 2026-09-21 借鏡 jl-delegation-workflow）**: 每次委派當下，除了 vpos_lead 之外，活躍的子代理（running status）**最多 2 個**。這是防卡死與上下文爆炸的硬上限——超過就表示派太開、監控會失焦。達上限時：(a) 先等現有子代理完成/停止，或 (b) 把多個小任務合併成「一個聚焦 goal」用單一子代理處理。**換專案（新工作目錄）也適用此鐵則**——它跟 vpos_lead profile 綁定、存在 `~/.hermes/profiles/vpos_lead/skills/vpos-delegation-workflow`，不隨 VPOS_Avalonia/ 目錄變動，因此任何專案都自動生效。
9. **Dev→QA 依賴順序（鐵則, 2026-09-21 TASK-030 教訓）**: `vpos_core`（或 vpos_ui）**完成寫入後**才派 `vpos_qa` 審查。**嚴禁把 dev 與 qa 並行派出**——qa 若讀到 dev 尚未寫入的過時檔案，會產出假陽性 REJECTED（TASK-030 首份報告就是因為并行委派、qa 在 12:12 grep / 12:16 git status 超時，而 HttpsFun.cs 實際寫入是 12:15:58 → 讀到 stale file）。並行委派不是中性的工程選擇，它就是 race condition 的根因之一。正確做法：(a) dev 完成 → (b) vpos_lead 獨立 grep 初步驗證 → (c) 才派 qa 正式審查；或 dev+qa 同一子代理依序執行。**例外**：只有當 dev 與 qa 審查的是「完全互不相干的兩個檔案/任務」時才可並行。
10. **Gateway 狀態交叉確認（2026-09-21 TASK-030 教訓）**: cronjob create/list 回傳的 `gateway_running` 欄位是「cron 會不會觸發」的權威來源，但**不可只信一個欄位就下結論**。當它回報 false 時，必須再直接跑一次 `hermes gateway status`（或 `systemctl --user status hermes-gateway-*.service`）交叉確認——工具欄位可能因服務尚未完全就緒、已退出、或與 cron 子系統檢查的 service unit 不同步而誤報。回報 false = 先 `hermes gateway start`，再重新建立 watchdog。

## 修正教訓 (User-Corrected Workflow Rules)

### 教訓 A: 全新開發功能必須完整流程 (使用者 2026-08-19 修正)
**問題**: 原流程只覆蓋「既有已知問題修復」，全新開發功能時沒有標準作業程序。

**完整流程 (全新功能)**：
1. **需求分析 (Requirement Analysis)**：釐清功能目標與使用者故事。
2. **強制 Graphify 圖譜分析 (Mandatory Step)**：
   - 執行 `graphify query "<功能名稱>"` 分析現有模組依賴。
   - 確認新功能的邊界 (Boundary) 與可能影響的既有程式碼。
   - 此步驟對「既有問題修復」與「全新開發」皆為**強制執行**。
3. **技術設計 (Technical Design)**：
   - 決定架構模式 (MVVM / Singleton / Service)。
   - 規劃資料模型 (Models/DTOs)。
4. **任務板建立 (Task Board Setup)**：
   - 在 `task_board.json` 建立主 Task (status=IN_PROGRESS)。
   - 拆解為 UI (`vpos_ui`) 與 Core (`vpos_core`) 的獨立子任務。
5. **微步委派與 Cron 監控**：(同既有問題修復流程)

### 教訓 B: 強制 Profile 載入機制 (使用者 2026-08-19 修正)
**問題**: 子代理可能在 `context` 中寫「你現在是 vpos_core」這種角色扮演，而非實體啟動 Profile。

**強制規範**：
- **❌ 禁止**：在 `context` 欄位寫「你是一位 C# 工程師，請修改 XXX」
- **❌ 禁止**：在 `context` 欄位寫「你現在是 vpos_core」角色扮演
- **✅ 強制**：透過系統 API 或 CLI 命令實體啟動對應 Profile。
  - 使用 `delegate_task` 時，在 `context` 明確指定 profile：`profile: vpos_core`
  - 或使用 CLI 命令：`hermes chat -q "<任務內容>" --profile vpos_core --cli`
  - 確保子代理載入的是專屬 Profile 的 Skills 與 Memory，而非共用主 Profile 的設定。

### 教訓 C: Cron-Ready 微步切割標準 (使用者 2026-08-19 修正)
**問題**: 任務拆分不夠細膩，導致子代理無法在 Cron 檢查週期內完成，造成卡死或超時。

**Cron-Ready Rule (任務大小限制)**：
- **目標完成時間**：單一 Task 必須能在 **10 分鐘內** 完成（約 2~3 次 Cron 檢查週期）。
- **切割原則**：
  - ❌ **太大**：「重構整個 `MainWindow.axaml.cs`」(會卡死/超時)
  - ✅ **剛好**：「將 `MainWindow.axaml.cs` L100-L200 的 `Click` 事件提取至 `MainWindowState.cs`」
  - ✅ **剛好**：「修復 `SqliteDataAccess.cs` 中 L50-L100 的 SQL 注入問題 (3 處)」
- **判斷指標**：若單一 Task 涉及超過 **3 個檔案** 或修改點超過 **5 處**，必須繼續拆分 (Micro-Batching)。
- **Cron repeat 動態調整**：簡單修復(≤5處)→3, 中等(5~20)→6, 大型重構(>20)→10。

| 任務規模 | 修改點數 | 檔案數 | Cron repeat | 預估完成時間 |
|---------|---------|-------|-------------|------------|
| 簡單修復 | ≤5 處 | ≤1 個 | 3 | <5 分鐘 |
| 中等修復 | 5~20 處 | ≤3 個 | 6 | 10~20 分鐘 |
|| 大型重構 | >20 處 | >3 個 | 10 | 30+ 分鐘 (需繼續拆分) |

### 教訓 D: TASK-030 [F6] HttpClient pooling — 並行委派 + 漏建 watchdog 的三連教訓（使用者 2026-09-21 逐項糾正）
**背景**: TASK-030 把 HttpsFun.cs 單一 static `_httpClient` 改為 `IHttpClientFactory` + `SocketsHttpHandler`（MaxConnectionsPerServer=100），消除 F6 連線池耗盡根因。程式碼本身正確、QA v2 PASS、TASK-030 DONE。但流程暴露三個漏洞，使用者逐一指出：

**漏洞① — gateway 狀態只信一個欄位**
- 現象: cronjob create 回傳 `gateway_running: false`，vpos_lead 據此回報「gateway 未啟動」。
- 根因: 工具欄位是權威來源但可能誤報（服務尚未完全就緒 / 已退出 / 與 cron 子系統檢查的 service unit 不同步）。使用者在對話前已在另一視窗 `hermes gateway start`。
- 修正: 回報 false 時**必須再跑一次 `hermes gateway status` 交叉確認**。此條已收進核心原則 #10。

**漏洞② — dev 與 qa 並行派出（最嚴重）**
- 現象: vpos_core 與 vpos_qa 在同一 `delegate_task` 裡並行送出，沒有等 core 改完才派 qa。
- 根因: 誤以為兩者獨立；並行委派不是中性選擇，它就是 race condition 的根因——qa 在 core 寫入前就 grep（12:12）/ git status 超時（12:16），而 HttpsFun.cs 實際寫入是 12:15:58 → qa 讀到 stale file → 假陽性 REJECTED。
- 修正: **Dev→QA 嚴格依序**：dev 完成 → vpos_lead 獨立 grep 初步驗證 → 才派 qa 正式審查。此條已收進核心原則 #9。

**漏洞③ — 重派 qa 時漏建 watchdog**
- 現象: 重派 re-verification qa（deleg_37d3cc2c）時，vpos_lead 隻手動 tail transcript + delegate_task list，沒有為這個新委派建立 cron watchdog。
- 根因: 以為「同一任務的第二次」可沿用舊 watchdog；或過度依賴手動檢查。
- 後果: 湊巧沒出事（靠手動盯），但若那次 qa 也卡死，沒有任何自動警報。這是明確的流程違規（陷阱22/40）。
- 修正: **每次 delegate_task（含重派 / re-dispatch）送出當下都必須立即建立 watchdog**，並回報新的 job_id + schedule。此條已收進「建立監控」段。

**教訓收斂**: TASK-030 的程式碼品質是正確的（QA v2 PASS），但流程面暴露「只信單一欄位」「並行破壞依賴順序」「重派漏建監控」三點。這三點已全部寫入核心原則 #9/#10 與建立監控段，未來任何委派都必須遵守 Dev→QA 依序、每次新委派必建 watchdog、gateway 狀態必交叉確認。**漏洞①的根因（vpos_lead 專屬 gateway service 未安裝）已於 2026-09-21 由 vpos_lead 自行 `hermes gateway install && hermes gateway start` 解決，並啟用 systemd linger；此後新增的「標準流程 Step 0.1 Gateway Bootstrap」確保每次新 session 開頭先確認 service active，從源頭避免 watchdog 不觸發。**

## 標準流程
0. **Graphify 圖譜維護與查詢 (任務前強制步驟)**:
   - 檢查 `graphify-out/GRAPH_REPORT.md` 最後修改時間。若超過 24 小時或涉及新檔案，執行增量更新：
     ```bash
     /graphify /media/sf_VPOS_Avalonia --update
     ```
   - 根據任務範圍執行 `graphify query "..."` 查詢相關模組依賴圖、呼叫鏈、community 邊界。
   - 將關鍵發現寫入 `review-reports/` 下的任務暫存檔，供子代理參考。
   - **⚠️ 分析任務時必須優先使用 graphify，grep 僅用於最終驗證。**

0.1. **Gateway Bootstrap（委派前強制步驟, TASK-030 教訓）**: cron watchdog 只有在 `hermes-gateway-vpos_lead.service` 執行時才會觸發。派單前**必須先確認該 service 存在且 active**，否則 watchdog 形同虛設：
   ```bash
   systemctl --user is-active hermes-gateway-vpos_lead.service   # 應回傳 active
   ```
   - **active** → 通過，繼續委派。
   - **inactive / not-found（unit 找不到）** → 一次性修復：`hermes gateway install && hermes gateway start`（install 會啟用 systemd linger，登出後仍存活），再 `systemctl --user is-active ...` 交叉確認回傳 active。**不可只信 cronjob create/list 回傳的 `gateway_running` 欄位**——它可能因 service unit 未安裝而永遠 false。
   - **⚠️ 資源提醒**: 每個 gateway ~126MB RAM；vpos_lead / jl_lead / default 三個可並存。保持 vpos_lead gateway 常駐是委派流程的合理需求（watchdog 依賴它），除非使用者要求省資源，否則維持常駐。
   - **每次新 session 開頭**都應執行一次 is-active 檢查；若 inactive/not-found 就 bootstrap。這比「派單後被 cron 回報 false 才發現」更早、更可靠。

   0.1.1. **Gateway 常駐韌性驗證（2026-09-22 借鏡 jl-delegation-workflow Step 0.1.1）**：`is-active` 只證明「現在在跑」，不保證「下次開 session 或電腦重啟後還在」。委派流程的 watchdog 依賴 gateway 常駐，所以**每次新 session 開頭（Step 0.1）應連同以下四項一起檢查**，缺一不可：

   ```bash
   systemctl --user is-active hermes-gateway-vpos_lead.service    # 1. active（現在在跑）
   loginctl show-user vblinux -p Linger                           # 2. Linger=yes（登出後仍活的关键）
   systemctl --user is-enabled hermes-gateway-vpos_lead.service   # 3. enabled（開機自動起）
   pgrep -af "hermes_cli.main.*vpos_lead.*gateway"                # 4. 實際 process + PID
   ```

   - **Linger=yes**：user systemd 服務跟帳號綁定，有 linger 時登出/登入都不會被清理。這是「對話結束後仍活」的關鍵開關——沒有 linger，帳號完全登出很長時間後 user manager 會隨之停止、gateway 被殺。
   - **enabled**：重啟電腦後開機自動啟動。
   - **Restart=always**（查 `systemctl --user cat hermes-gateway-vpos_lead.service`）：萬一它崩了，systemd 5 秒後自動拉起（Exit 78 除外）。
   - **實際 process / PID**：`is-active` 回傳 active 代表一定有 process 在跑；用 `pgrep -af "hermes_cli.main.*vpos_lead.*gateway"` 抓到真實 PID（command line 是 `python -m hermes_cli.main --profile vpos_lead gateway run`）。

   **四項全過 = gateway 真常駐**：對話結束、你登出登入都不影響；唯一會讓它停的是手動 `systemctl --user stop`、整台關機/重啟（enabled 會幫它在下次開機自動回來）、或 linger 被關閉且帳號完全登出很長時間。

0.5. **Hermes_BK 備份觸發條件鐵律（2026-09-23 使用者修正）**:
   > ⚠️ **只在「系統重灌後無法自動生成」的資料發生異動時才執行 `bash /home/vblinux/Hermes_BK/backup.sh`**：
   > - ✅ **觸發備份（持久化系統資料異動）**: 新增／修改 skill（SKILL.md）、寫入／更新 memory、跨 profile 分發或同步技能、借鏡其他 profile 後回補、改 SOUL.md / config.yaml / cron。
   > - ❌ **不觸發備份（專案可重生成物）**: `docs/task_board.json`、`review-reports/issue-log.md`、所有 `.cs/.axaml` 原始碼、`FlaUI_Test/`、`NSIS_Project/`。這些在 git 或程式下都能重建，**QA PASS / 更新 task_board 後一律不執行備份**。
   > - **判断口訣：「改的是專案產物就別備，改的是系統記憶才要備」**。
0.6. **task_board.json 三階段生命周期（TASK-009 教訓）**:
   - **完整流程與範例**: `references/task-board-lifecycle.md`
   - **Phase 1 (Step 0.5, 分析時)**: Graphify 完成後、派單前，讀取 task_board.json。若任務不存在 → 建立物件（status=IN_PROGRESS）。更新 last_updated + python3 驗證。（task_board.json 是專案檔，**不觸發 Hermes_BK 備份**）
   - **Phase 2 (子代理完成)**: 子代理標 status=REVIEW，附上 ls -la + grep 驗證結果。派單提醒：「完成後請將 task_board.json 中 Task 狀態更新為 REVIEW，並附上 ls -la 與 grep 實體寫入驗證結果。」
   - **Phase 3 (QA PASS 後)**: vpos_lead QA PASS → status=DONE + qa_review="PASS" + qa_review_file + completed_date。更新 last_updated + python3 驗證。（task_board.json 是專案檔，**不觸發 Hermes_BK 備份**）

1. **問題分析與微步拆分 SOP (Micro-Batching Workflow)**:
   - **🚫 防重工（2026-09-21 借鏡 jl-delegation-workflow）**: 派單前**必須先讀取 `docs/task_board.json` 與 `review-reports/issue-log.md`**，確認該需求是否已完成：
     - **已完成且 DONE** → 直接告知使用者已實作，嚴禁盲目重複。
     - **未完成（TODO/IN_PROGRESS/REVIEW/REJECTED）** → 接續既有工單，不重建。
     - **全新需求** → 建立 Task（status=TODO）→ 派單。
     - **「還有哪些未完成」類問題**：不得只信 task_board 或單一 checklist——至少交叉比對 task_board / gap-analysis.md（勾選框常過時）/ issue-log.md（REJECTED 可能已被親自重做標 DONE）。細節見 `references/task-board-lifecycle.md`。
   - **軌道 A (現有問題修復)**: 閱讀 `review-reports/02_問題詳細說明與檔案對應表.md`，結合 graphify 查詢結果拆解為單一原子任務。
   - **軌道 B (全新開發項目)**: Graphify 全域探索 → 確認需求 → 建立 `docs/` 任務板 → 派單。
   - **大範圍修改拆分原則**: 若單一檔案修改點 >3 處或涉及多個檔案，`vpos_lead` 必須執行微步拆分：
     - 在 `task_board.json` 中將大任務拆解為 `TASK-XXXa`, `TASK-XXXb` 等微型工單（Micro-Tasks），每次派單僅處理 1~2 處精準變更。
     - **Context 預載 (Pre-Hydration)**: 派單時必須直接附上目標檔案的精準行號範圍與修改前後的預期程式碼 Snippet，避免子代理閱讀整份巨大檔案[cite: 5]。

2. **任務委派與 Context 預載**:
   - 後端/DB/硬體 → `vpos_core` (工作目錄: `DBLib/`, `WinAPI/`, `ToolLib/`, `Thread/`)[cite: 5]
   - UI/AXAML/ViewModel → `vpos_ui` (工作目錄: `Views/`, `ViewModels/`, `UserControl/`)[cite: 5]
   - **關鍵**: 委派時必須明確告知「工作目錄限制」、「開發約束條款」與「強制檢查清單 (Definition of Done)」[cite: 5]。

## 建立監控 (派單後立即執行):
- `cronjob(action='create')`，`schedule: every 3m`，`repeat: 10`[cite: 5]
- `prompt`: 檢查子代理狀態、檔案修改痕跡、回報進度或卡死[cite: 5]。
- **🔥 每次 delegate_task（含重派 / re-dispatch）送出當下都必須立即建立 watchdog，不可因為「同一任務的第二次」就省略**。重派 qa 複查、退回開發者重修、任何新的子代理委派 = 一個新的監控週期 = 一個新的 cron job。TASK-030 教訓：重派 re-verification qa（deleg_37d3cc2c）時只手動 tail transcript，**沒有為它建 watchdog**——靠手動檢查湊巧沒出事，但「湊巧成功」不等於流程正確。若那次 qa 也卡死，沒有 watchdog 會自動警報。**派單後回應必須包含 watchdog job_id + schedule；重派時也要重新建並回報新的 job_id**。

### ⚠️ Cron 零豁免與 Gateway 強制規範（2026-09-21 借鏡 jl-delegation-workflow）
1. **Gateway 必須在跑**: Linux 上 cron job 只有在 gateway 服務執行時才會觸發。派單前先確認 `systemctl --user status hermes-gateway-vpos_lead.service`（或 `hermes gateway status`）顯示 `active (running)`；若未跑，先 `hermes gateway install && hermes gateway start`。cron job 已建立但 gateway 沒跑 = 不會觸發 = 形同虛設。
2. **零豁免**: 任何委派（含「只改一個檔案、機械式批量替換」的任務）都必須在送出 `delegate_task` 當下立即建立 watchdog，不得以「任務太小/太快完成」為由跳過。漏建 watchdog 視為流程違規。
3. **回應必報**: 每次委派後的回覆中，必須明確列出 watchdog job_id 與 schedule；沒有就代表沒建。
4. **清理過期**: 舊 watchdog repeat 到點後會自動結束，若清單堆積已到期、無對應進行中任務的 watchdog，應主動 `cronjob action='remove'` 刪除，避免垃圾累積。

4. **子代理委派（vpos_core / vpos_ui）**：
   - **優先使用 `delegate_task`**：CLI 委派 (`hermes chat --profile`) 在 CLI/TUI 環境中常被使用者拒絕同意（exit_code=-1, BLOCKED），需改用 `delegate_task(goal=..., context=...)`。
   - **delegate_task 派單格式**: 在 `context` 欄位明確指定 profile、工作目錄、任務範圍；在 `goal` 欄位寫完整修改說明。
   - **⚠️ dispatch 後 5 分鐘內必須主動檢查 `delegate_task(action='list')`**。
   - **⚠️ 每輪開頭必須檢查是否有 pending 的 delegate_task**。

4b. **QA 審查（vpos_qa）**：
   - **子代理委派優先**: `hermes chat -q "..." --profile vpos_qa --cli --toolsets terminal,file`[cite: 5]
   - **⚠️ CLI 委派限制**: 若 `-q` 超時 (>120s) 或 Unicode 錯誤，**vpos_lead 手動審查**[cite: 5]。
   - **⚠️ vpos_qa delegate_task 卡死處理 (TASK-010a 教訓)**: 若委派 vpos_qa 後超過 15 分鐘 review-reports/ 仍無 TASK-XXX 報告，**vpos_lead 手動 grep 驗證並直接更新 task_board.json**。不要無限等待。
   - **手動審查流程**: `grep "_sharedConnection.Query" <檔案> | wc -l` → 確認數量符合預期 → 寫入 review-reports/review-TASK-XXX-*.md → 更新 task_board.json status=DONE + qa_review="PASS"[cite: 5]。

5. **通知使用者**: QA PASS 後通知使用者驗收，等待明確指示才繼續下一個任務[cite: 5].
   - **回報原則**: 使用者要「最終結果」而非每次微步都報。只在以下時機回報：
     (a) Task 完成（QA PASS）→ 回報修改摘要 + 請使用者編譯驗收
     (b) Task 失敗/卡死 → 回報錯誤與處理方式
   - **不要**在每個 micro-task dispatch、verify、patch 時都回報，除非使用者主動問「進度？」。
   - ⚠️ **待命模式鐵律 (TASK-015/016 教訓)**: QA PASS 通知使用者後必須停下等待。除非使用者說「繼續」否則不主動派新任務、不跳去分析下一個問題。不可連續處理多個 Task 而不間隔。

6. **子代理卡死處理**:
   - 若子代理連續兩次委派超過 9 分鐘沒有產出（如 TASK-013b），`vpos_lead` 改用 `execute_code` (Python) + regex 進行機械式批量替換：
     1. 先 `read_file` 取得目標類別的實際屬性名稱（source of truth）
     2. 用 Python regex 找出所有錯誤引用
     3. 建立 wrong→correct mapping table，批量替換
   - 參考: `references/giant-codebehind-refactor-pattern.md` (陷阱5)

7. **DllImport 提取模式**:
   - 將 `[DllImport]` extern + 常數提取至獨立 ToolLib 類別（如 WinApiHelper.cs）
   - namespace 改為 `VPOS_Avalonia.ToolLib`，所有呼叫端改為 `WinApiHelper.MethodName()`
   - 參考: `references/winapi-dllimport-extraction.md`

## vpos_lead patching vs delegate_task 決策樹 (2026-08-13)
- **單一檔案 ≤3 處修改** → **優先委派給下屬**（TASK-015~018 教訓：vpos_lead 過度依賴 patch）
- **單一檔案 >3 處相同 rename** → vpos_lead 用 `patch(replace_all=True)` 直接處理（機械式 regex 替換）
- **新增單一欄位/方法** → vpos_lead 直接 patch（最簡單的機械操作）
- **多檔案 cascade（>2 個檔案）** → delegate `vpos_core`（附完整錯誤清單）
- **需要商業邏輯判斷** → delegate（非機械式操作）

### execute_code vs delegate_task 選擇
- **delegate_task**: 需要理解商業邏輯、跨檔案關聯、設計決策（如 SQL 注入修復）
- **execute_code**: 機械式批量替換、grep/count/verify、regex 全文搜尋替換、屬性名稱映射

## HttpClient 重構常見陷阱 (TASK-007a/b)

### 陷阱1: setHeader() 被遺漏 → Header 支援失效
**問題**: 子代理將 HttpWebRequest 替換為 `_httpClient.GetAsync(url)`，但遺漏了 `setHeader()` 功能（Authorization、自訂 Header）。所有呼叫端依賴此機制傳送驗證資訊。

**修復方式**: 改用 `HttpRequestMessage` + `_httpClient.SendAsync(request)`：
```csharp
var request = new HttpRequestMessage(HttpMethod.Get, url);
if (StrHeaderName.Length > 0 && StrHeaderValue.Length > 0)
{
    request.Headers.Add(StrHeaderName, StrHeaderValue);
}
var response = _httpClient.SendAsync(request).GetAwaiter().GetResult();
```

**派單時必附提醒**: "注意：需支援自訂 Header（如 Authorization: Basic ***），使用 HttpRequestMessage + SendAsync，勿用 GetAsync。"

### 陷阱2: CS0136 重複宣告
`#if DEBUG` 區塊內若有多處 `String StrLog = String.Format(...)` 會觸發 CS0136（同一方法範圍內同名變數）。修復方式：inline `LogFile.Write("...")` 直接寫入，不宣告中間變數。

### 陷阱3: HttpRequestMessage 計數誤判
驗證時 `grep "HttpRequestMessage"` 會同時抓到註解行（如 `// HttpClient: use HttpRequestMessage`），實際應檢查 `new HttpRequestMessage(HttpMethod.Get` 而非單純 grep 類別名。

### 陷阱4: #if DEBUG 區塊範圍誤判
驗證腳本若用固定行號範圍（如 L198-325）可能漏掉超出範圍的程式碼。建議改用方法簽名動態計算範圍，或直接 grep 全檔案後人工確認。

## MainWindowState.cs 編譯錯誤 cascade 處理模式 (TASK-014)

### 陷阱5: 子代理卡死於大型檔案重構 (TASK-013b)
**問題**: `vpos_core` 連續兩次委派都超過 9 分鐘沒有產出（54 個 public static 成員 → MainWindowState singleton）。原因：子代理需要讀取 12,368 行的巨大檔案，認知負載過高。

**修復方式**: `vpos_lead` 改用 `execute_code` (Python) + regex 進行機械式批量替換：
1. 先 `read_file` 取得 MainWindowState.cs 的實際屬性名稱（source of truth）
2. 用 Python regex 找出所有錯誤引用 (`Instance.mterminalpanelstyles`)
3. 建立 wrong→correct mapping table，批量替換

### 陷阱6: MainWindowState 屬性命名慣例 (m_XXX → mXxx)
**問題**: vpos_core 的 regex 把 `m_terminal_panel_styles` 轉成 `terminalpanelstyles`（扁平連接），但正確應該是 `mTerminalPanelStyles`（駝色，保留 m_ 前綴後接 CamelCase）。

**命名規則**: `m_FieldName` → `mFieldName` (去掉底線，每個單字首字母大寫)
- `m_intOrderTypeIdSelected` → `mIntOrderTypeIdSelected` ✅
- `m_terminal_panel_styles` → `mTerminalPanelStyles` ✅
- `m_VTSTORE_params` → `mVTSTORE_params` ✅ (VTSTORE 全大寫不拆)

**派單時必附提醒**: "屬性命名慣例：m_XXX → mXxx（駝色，保留 m_ 前綴）。例如 m_intOrderTypeIdSelected → mIntOrderTypeIdSelected。"

### 陷阱7: MainWindowState.cs 屬性名稱必須作為 source of truth
**問題 (TASK-013b)**: vpos_core 產出的 MainWindowState.cs 有實際的屬性名稱（如 `mTerminalPanelStyles`），但 MainWindow.axaml.cs 中的 forwarding property 引用了錯誤的名稱（如 `Instance.mterminalpanelstyles`）。直接 patch MainWindow.axaml.cs 會因為找不到 match 而失敗。

**修復流程**：
1. **先讀取 MainWindowState.cs** — 用 `grep 'public.*\w+\s+\w+' VPOS_Avalonia/ViewModels/MainWindowState.cs` 取得所有實際屬性名稱
2. **再 grep MainWindow.axaml.cs** — 找出所有 `MainWindowState.Instance.XXX` 引用，比對哪些是錯誤的
3. **建立 wrong→correct mapping table** — 用 Python regex 批量替換（而非 patch）

**派單時必附提醒**: "完成後請先 `read_file` MainWindowState.cs 確認實際屬性名稱，再修改 MainWindow.axaml.cs 的引用。"

### 陷阱8: CS0246 / CS0103 連鎖錯誤 — 根因是缺少 using，不是類別不存在
**問題**: `MainWindowState.cs` 引用了定義在 `VPOS`、`VPOS_Avalonia.DBLib`、`VPOS_Avalonia.ToolLib` namespace 下的類別，但檔案開頭只有基本 using。編譯器回報 ~100+ 個 CS0246/CS0103 錯誤，看起來像「找不到類別」，實際只需補上 3 行 using。

**常見缺失的 using：**
```csharp
using VPOS;                          // UBER_EATS_params, ShopCart, func_mainData, getorderno, terminal_panel_styles...
using VPOS_Avalonia.DBLib;           // SQLDataTableModel, SqliteDataAccess
using VPOS_Avalonia.ToolLib;         // JsonClassConvert, VP_Convert, LogFile, HttpsFun, TimeConvert...
```

**處理流程：**
1. **先 grep 分類錯誤中的類別名** — `search_files(pattern="class UBER_EATS_params")` → 確認 namespace
2. **一次 patch 補上所有需要的 using**（不要拆成多個 micro-task）
3. **特別注意兩個容易遺漏的類別：**
   - `SerialCodeDataGet` — 是 MainWindow.axaml.cs 的 public static method (line ~11238)，不是獨立 class
   - `FileLib` — grep 確認其 namespace

**派單時必附提醒**: "先 grep 所有錯誤中的類別名，確認它們的 namespace，然後一次 patch 補上所有 using。不要拆成多個任務。"

### 陷阱9: CS0122 保護層級錯誤 — MainWindowState 存取 private 成員
**問題**: `MainWindowState.cs` (ViewModels) 需要存取 `MainWindow.axaml.cs` (Views) 的成員，但那些成員宣告為 private（無 public/internal），導致 ~47~157 個 CS0122 錯誤。

**需改為 internal 的典型成員（含欄位、陣列、方法）：**
```csharp
// 欄位/陣列 (line ~201-205, ~1342, ~1541, ~2587)
internal CustBtn[] m_OrderBtn;
internal BadgeButton VTSTOREBtn;
internal BadgeButton TakeawayOrdersBtn;
internal BadgeButton VTEAMQrorderBtn;
internal CustBtn MemberBtn;
internal CustBtn[] m_CategoryBtn;
internal CustBtn[] m_ProductBtn;
internal CustBtn[] m_CondimentBtn;
internal string[] m_strShopcartBtnName;

// 方法 (line ~439, ~511, ~597, ~2940, ~3607, ~4819)
internal async void PackagingBtn_Click(object sender, RoutedEventArgs e);
internal async void MemberBtn_Click(object sender, RoutedEventArgs e);
internal async void ExternalOrderBtn_Click(object sender, RoutedEventArgs e);
internal void DiDiMoneyInfoGridSet(bool blnSQL = true);
internal async void DiDiMoneyBtn_Clicked(object sender, RoutedEventArgs e);
internal async void ShopcartItemEdit_Clicked(object sender, RoutedEventArgs e);
```

**處理流程：**
1. grep CS0122 錯誤中的成員名，確認它們在 MainWindow.axaml.cs 的宣告行號
2. patch 將 private → internal（不是 public，因為 ViewModel 不需要外部存取）
3. **注意**: `m_OrderBtnSelected` (line ~206) 已經是 public，不需修改；`GetShopCartVarIndex` (line ~4408) 已經是 public，不需修改

**派單時必附提醒**: "只改 private → internal，不改 public。確認成員名在 MainWindow.axaml.cs 的實際行號再 patch。注意：包含方法宣告也要一起改。"

### 陷阱10: CS1061 — VTSTOREAPI 等 API 類別的 namespace 未被 using
**問題**: `MainWindowState.cs` line 374, 1354, 1380 使用 `VTSTOREAPI.m_intVTSTOREButtonIndex`，但 VTSTOREAPI 定義在 `VPOS_Avalonia/WebAPI/` 下，需要對應的 using。

**處理流程：**
1. grep 找到 VTSTOREAPI 的 namespace（通常在 VPOS_Avalonia/WebAPI/）
2. 確認 MainWindowState.cs 的 using 是否已涵蓋（若 vpos_ui 已補上 `using VPOS_Avalonia.ToolLib;`，檢查 ToolLib 是否有 re-export）

**派單時必附提醒**: "grep VTSTOREAPI 找到其 namespace，確認 using 是否已涵蓋。"

### 陷阱11: Constructor body 欄位名必須與宣告一致（不只是方法體內）
**問題 (TASK-A)**: MainWindowState.cs constructor (lines ~39-63) 使用了舊版底線命名（`m_ClassLastTime`, `m_StrVersion`），但 class-level 宣告已經是 PascalCase（`mClassLastTime`, `mStrVersion`）。Constructor 內的賦值也會觸發 CS0103。

**修復方式**: Constructor 內所有欄位引用必須與宣告完全一致：
```csharp
// ❌ 舊版 constructor
m_ClassLastTime = DateTime.Now;       // CS0103: 找不到 m_ClassLastTime
m_StrVersion = "";                    // CS0103

// ✅ 修正後
mClassLastTime = DateTime.Now;        // 與宣告一致
mStrVersion = "";                     // 與宣告一致
```

**派單時必附提醒**: "Constructor body 內的欄位賦值也要檢查命名是否與 class-level 宣告一致。不要只改方法體內的引用。"

### 陷阱12: MainWindowState 缺少從 MainWindow.axaml.cs 遷移的欄位
**問題 (TASK-B)**: `MainWindowState` singleton 需要某些欄位（如 `m_strShopcartBtnName`, `mBlnScrollTo`, `mIntOrderState`），但這些欄位在 MainWindow.axaml.cs 中存在，卻沒有被遷移到 MainWindowState。當 MainWindowState 的方法引用它們時會觸發 CS0103/CS0122。

**處理流程：**
1. grep MainWindowState.cs 中所有未定義的欄位名（如 `m_strShopcartBtnName`）
2. 在 MainWindow.axaml.cs 中找到原始宣告，確認型別與預設值
3. 將完整宣告複製到 MainWindowState.cs 的適當 #region 區塊內

**派單時必附提醒**: "檢查 MainWindowState 中所有未定義的欄位引用，從 MainWindow.axaml.cs 找到原始宣告並遷移。"

### 陷阱13: VTSTOREAPI 是 static class — 用直接靜態存取，不用 `mw.` 前綴
**問題 (TASK-E)**: `MainWindowState.cs` line 1374, 1400 使用 `mw.VTSTOREAPI.m_intVTSTOREButtonIndex = j;`。但 VTSTOREAPI 是 `VPOS` namespace 下的 **static class**（定義在 `VPOS_Avalonia/WebAPI/VTSTOREAPI.cs`），不是 MainWindow 的 instance member。

**修復方式**: 去掉 `mw.` 前綴，直接靜態存取：
```csharp
// ❌ 錯誤 — VTSTOREAPI 不是 MainWindow 的成員
mw.VTSTOREAPI.m_intVTSTOREButtonIndex = j;

// ✅ 正確 — static class 直接存取
VTSTOREAPI.m_intVTSTOREButtonIndex = j;
```

**注意**: `using VPOS;` 已在 MainWindowState.cs line 16，無需額外 using。

**派單時必附提醒**: "grep VTSTOREAPI 確認它是 static class（namespace VPOS），所有引用去掉 mw. 前綴直接存取。"

### 陷阱14: MainWindowState static event handler wrappers — async void 不可 await
**問題**: MainWindowState.cs 的靜態 wrapper 使用 `async void ... => await ((MainWindow)sender).Method()`，但目標方法已是 `private async void`。C# 不允許 `await` 一個 `void` 方法（CS1998）。

**修復方式**: 移除 `await` 和 `async`，改為純 `void` wrapper：
```csharp
// ❌ 錯誤 — await on void method (CS1998)
public static async void ShopcartBtn_Clicked(object sender, RoutedEventArgs e) => await ((MainWindow)sender).ShopcartBtn_Clicked(sender, e);

// ✅ 正確 — void wrapper，不 await
public static void ShopcartBtn_Clicked(object sender, RoutedEventArgs e) => ((MainWindow)sender).ShopcartBtn_Clicked(sender, e);
```

**例外**: 若目標方法是 `private void`（非 async），同樣用 `void` wrapper。若目標是 `private Task Method()`，則 wrapper 可用 `async void ... => await ((MainWindow)sender).Method(sender, e)`。

**派單時必附提醒**: "檢查 MainWindowState.cs 的 event handler wrappers — 所有 `await ((MainWindow)sender)` 都必須確認目標方法回傳型別。若目標是 async void，wrapper 也必須是 void（不 await）。"

### 陷阱15: No-parameter event handler wrapper 缺少 sender 參數
**問題**: MainWindow.axaml.cs 有兩個 `CategoryBtn_Clicked` overload：無參數版和 `(object sender, RoutedEventArgs e)` 版。MainWindowState.cs line 1957 的 wrapper 宣告為 `CategoryBtn_Clicked()`（無參數），但 body 內用了 `sender`：
```csharp
public static async void CategoryBtn_Clicked() => await ((MainWindow)sender).CategoryBtn_Clicked();
// ❌ 'sender' does not exist in current context
```

**修復方式**: 移除無參數 wrapper，或改為有 sender 參數的正確 signature。通常直接刪除多餘的無參數 overload：
```csharp
// 只保留有參數版（與 MainWindow.axaml.cs 的 overload 匹配）
public static void CategoryBtn_Clicked(object sender, RoutedEventArgs e) => ((MainWindow)sender).CategoryBtn_Clicked(sender, e);
```

**派單時必附提醒**: "檢查所有無參數 wrapper（如 `CategoryBtn_Clicked()`），確認 body 內是否有使用 sender。若有，改為有參數 signature 或移除該 overload。"

### 陷阱16: m_XXX vs mXxx 命名不一致 (TASK-009)
**問題**: MainWindowState.cs line 269 欄位定義為 `public ShopCart mShopCart = null;`（無底線，camelCase），但 lines 1716, 1721, 1724, 1727, 1734 使用 `m_ShopCart.m_ShopMainList`（多一個底線）。編譯器回報 CS0103「名稱不存在於目前的內容中」。

**與陷阱6的區別**:
- **陷阱6 (m_XXX → mXxx)**: regex 轉換錯誤，把 `m_terminal_panel_styles` 轉成扁平連接 `terminalpanelstyles`
- **陷阱16 (m_XXX vs mXxx)**: 定義用一種風格（無底線 camelCase），使用處用另一種風格（有底線 snake-style）

**處理流程**:
1. **grep 確認定義處的實際名稱** — `grep "public.*ShopCart" MainWindowState.cs` → 看到 `mShopCart`（無底線）
2. **grep 確認使用處的名稱** — `grep -n "m_ShopCart\|mShopCart" MainWindowState.cs` → 比對差異
3. **patch 統一為定義處的名稱** — 所有 `m_ShopCart` → `mShopCart`

**派單時必附提醒**: "先 grep 確認欄位定義處的實際名稱（source of truth），再 patch 使用處以匹配。不要假設定義和使用的命名風格一致。"

## Connection Pooling 陷阱 (TASK-010)

### 陷阱17: GetSharedConnection() 被宣告但未被呼叫
**問題**: vpos_core 寫了 `GetSharedConnection()` 函數（double-check locking），但忘了在 Load() 方法中使用它。所有 `_sharedConnection.Query` 都是直接存取，沒有先初始化連接。導致 `_sharedConnection` 為 null，執行時拋出 NullReferenceException。

**修復方式**: vpos_lead 用 `patch(replace_all=True)` 將所有 `_sharedConnection.Query` 改為 `GetSharedConnection().Query`：
```bash
# 驗證
grep "_sharedConnection.Query" <檔案> | wc -l → 應為 0
grep "GetSharedConnection().Query" <檔案> | wc -l → 應 >= 56
```

**派單時必附提醒**: "注意：所有 `_sharedConnection.Query` 必須改為 `GetSharedConnection().Query`，確保連接先初始化。不要直接存取 `_sharedConnection`。"

### 陷阱18: sibling subagent 修改 task_board.json 導致 patch JSON 語法錯誤
**問題 (TASK-010a/b)**: vpos_qa 的 delegate_task 子代理嘗試更新 task_board.json，但同時 vpos_lead 也對同一檔案執行 `patch`。由於 sibling subagent 可能已修改內容，vpos_lead 的 patch fuzzy matching 會匹配到舊行號，導致 JSON 語法錯誤（JSONDecodeError: Expecting ',' delimiter）。

**修復方式**:
1. **先讀取 task_board.json** → 確認當前狀態
2. **若 sibling subagent 可能已修改** → 使用 `write_file` 完整重寫而非 `patch`
3. **不要依賴 patch 的 fuzzy matching** 處理 JSON 檔案（JSON 對格式敏感，fuzzy matching 容易失敗）

**派單時必附提醒**: "若 sibling subagent 可能已修改 task_board.json，請使用 write_file 完整重寫而非 patch。"

## Patch Complete 鐵律 (TASK-015~018)
### 陷阱19: vpos_lead Patch Complete 後忘記通知使用者驗收（最嚴重的流程漏洞）
**問題**: 每次 vpos_lead 直接 patch/write_file 完成任務後，自動跳到「更新 task_board → 分析下一個問題」，沒有強制停下來通知使用者編譯驗收。記憶中有寫「QA PASS 通知使用者後必須停下等待」，但 vpos_lead 手動 grep 驗證不算 QA PASS，所以跳過了通知步驟。

**根因**: delegate_task 有 cron watchdog 自然形成間隔；vpos_lead 直接 patch 沒有檢查點。**更關鍵的是：同一輪內 patch + 更新 task_board + 分析下一題 → 使用者看到新任務以為在繼續做，沒注意到要驗收。**

**修復方式 — Patch Complete 鐵律（2026-08-13 新增）**：
每次 vpos_lead 執行 `patch` 或 `write_file` **修改了 VPOS_Avalonia/ 下的任何 .cs/.axaml 檔案後**，必須執行以下檢查流程：

```
PATCH/WRITE_FILE → grep 驗證 
    ↓
[檢查點] 同一 Task 還有其他 patch 要做嗎？
    ├─ 是（≤3次）→ 繼續 patch（不更新 task_board）
    └─ 否（最後一次或超過3次）→ 回報修改摘要 + "請編譯驗收" + 停下等待
        ↓ 使用者回覆「繼續」後 → 才更新 task_board.json (DONE) + 分析下一題
```

**關鍵規則**:
1. **單一 Task 內允許連續 patch ≤3 次**（例如：先加 field、再改 using、再修引用），這是合理的
2. **超過 3 次或不同檔案的 patch → 必須停下來通知使用者**
3. **task_board.json 的 DONE 狀態在「通知使用者後」才更新，不是 patch 完就更新**
4. **每次 patch/write_file 後，在回應結尾加上 `[PATCH]` 標記**，讓下一輪開始時檢查是否已通知

**[PATCH] 標記格式**:
```
[PATCH] <file>:<line> - <brief description>
```

**範例**:
```
[PATCH] JsonClassConvert.cs:22 - Added s_jsonOptions field
[PATCH] JsonClassConvert.cs:37 - Changed Serialize to use s_jsonOptions

✅ TASK-017 完成。請編譯驗收後回覆「繼續」再處理下一個 Task。
（task_board.json 尚未更新為 DONE，等你確認後才改）
```

**如果連續 patch 超過 3 次還沒通知使用者 → 下一輪開頭先檢查上一輪是否有 [PATCH] 標記但沒通知 → 補上通知**。

## JSON Serialization 陷阱 (TASK-017)
### 陷阱20: JsonSerializerOptions.DefaultIgnoreCondition = WhenWritingNull ≠ Replace("null","\"\"")
**問題**: `DefaultIgnoreCondition = WhenWritingNull` 會讓 null string 屬性**完全不出現在 JSON 中**。當這段 JSON 再被反序列化時，缺少的欄位拿不到值（仍是 null），而不是舊版 `.Replace("null", "\"\"")` 產生的 `""`（空字串）。

**錯誤示範**:
```csharp
// ❌ null string → 欄位消失
private static readonly JsonSerializerOptions s_jsonOptions = new()
{
    DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    WriteIndented = false
};
// 結果: {"Name":"Test"} — Address 和 Email 完全消失
```

**正確做法**: 用自訂 `JsonConverter<string?>` 把 null string 轉成 `""`（空字串），保持欄位存在於 JSON 中：
```csharp
private static readonly JsonSerializerOptions s_jsonOptions;

static JsonClassConvert()
{
    s_jsonOptions = new JsonSerializerOptions
    {
        WriteIndented = false,
        Converters = { new NullStringToEmptyConverter() }
    };
}

public class NullStringToEmptyConverter : JsonConverter<string?>
{
    public override string? Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        => reader.GetString();

    public override void Write(Utf8JsonWriter writer, string? value, JsonSerializerOptions options)
        => writer.WriteStringValue(value ?? "");
}
```

**效果對比**:
| 方法 | null string → ? | 欄位存在? | 影響非字串型別? |
|---|---|---|---|
| Replace("null","\"\"") | `""` | ✅ | ❌ numeric null 也變 "" |
| WhenWritingNull (錯誤) | 消失 | ❌ | — |
| NullStringToEmptyConverter (正確) | `""` | ✅ | ✅ 只影響 string |

**派單時必附提醒**: "若需取代 .Replace(\"null\", \"\\\"\\\"\"），使用自訂 JsonConverter<string?> 把 null → \"\"（空字串），勿用 DefaultIgnoreCondition=WhenWritingNull（會省略欄位）。"

### 陷阱21: C# static constructor 不需要 explicit 引用 (TASK-017 使用者提醒)
**問題**: 子代理或 vpos_lead 可能質疑 `static JsonClassConvert()` 靜態建構子「沒被引用過」，認為需要額外呼叫。

**事實**: C# runtime 會在**第一次存取任何 static member 時自動執行**靜態建構子（ECMA-335 §12.6.4）。例如：
```csharp
// Program.cs:47 — 這行就會觸發 static constructor
VLCS VLCSBuf = JsonClassConvert.VLCS2Class(StrVLCS);
```

不需要任何額外的 `new JsonClassConvert()` 或 explicit call。所有 `JsonClassConvert.XXX2String()` 靜態方法呼叫都會觸發它。

**派單時必附提醒**: "static constructor 不需 explicit 引用，C# runtime 會在第一次存取 static member 時自動執行。"

### 陷阱22: delegate_task 後忘記建立 Cron 監控 (TASK-019 教訓)
**問題**: `delegate_task` 送出子代理後，vpos_lead 直接跳到「更新 task_board.json → 分析下一個問題」，沒有先建立 Cron watchdog。使用者必須主動問「你有按照規定 建立定時監控嗎？」才補上。

**根因**: 流程中「建立監控」在「子代理委派」之前（Step 3 vs Step 4），但實際執行時是先 dispatch delegate_task（因為要等它回傳 delegation_id），然後才回頭建 cron。**如果只靠記憶而不檢查，很容易漏掉。**

**修復方式 — 派單後立即檢查清單**：
每次 `delegate_task` 完成後，在回應中**必須包含以下兩行**：
```
✅ delegate_task 已派出 (delegation_id: deleg_XXXXX)
📋 Cron watchdog 已建立 (job_id: XXXXX, schedule: every 3m)
```

如果因為某種原因沒建 cron（例如使用者要求先分析再派單），在回應中明確標註：
```
⏳ Cron watchdog 待建立（等確認後再建）
```

**每輪開頭檢查**: 若上一輪有 `delegate_task` 但沒有 job_id，這輪開頭立即補建 cron。

**派單時必附提醒**: "delegate_task 完成後，立即建立 Cron watchdog (every 3m, repeat=10)，並回報 job_id。"

### 陷阱40: 完全忘記建立 Cron 監控 (TASK-014-A8 教訓)
**問題**: vpos_lead 在派發 delegate_task 後，**完全沒有建立 Cron watchdog**。QA 子代理跑了 29 分鐘都沒有任何監控回報。這是比「遺漏」更嚴重的「完全跳過」。

**根因**: 過度依賴系統自動通知 (ASYNC DELEGATION BATCH COMPLETE)，認為「系統會通知我」，所以沒有建立 Cron。但 Cron 是**防呆機制**，不是「可有可無」的。

**修復方式**：
1. 每次 `delegate_task` 完成後，**立即**執行 `cronjob(action='create')`
2. **不可**因為「系統會自動通知」就跳過 Cron
3. 每輪開頭必須檢查 `cronjob(action='list')` 確認所有進行中任務都有對應 Cron
4. 若發現缺少 Cron，**立即補建**

**每輪開頭檢查清單**：
- [ ] 上一輪有 delegate_task 嗎？
- [ ] 有對應的 Cron job 嗎？
- [ ] Cron job 是否正常執行？
- [ ] 若任一個答案為「否」，立即補建

**派單時必附提醒**: "delegate_task 完成後，**必須立即**建立 Cron watchdog。不可跳過、不可依賴系統自動通知。每輪開頭檢查 Cron 狀態。"

### 陷阱23: System.Drawing → ImageSharp API 簽名改變 cascade (TASK-019)
**問題**: `BitmapBase64_Funs.cs` 的 `Image2Base64String(Bitmap)` / `Base64String2Image(string)` 方法簽名改為 `SixLabors.ImageSharp.Image`，但所有呼叫端（CS_PrintTemplate, orders_new, Login.axaml）沒有同步修改變數宣告。

**根因**: ImageSharp 的 `Image.Load(path)` 回傳 `SixLabors.ImageSharp.Image`（泛型），不是 `System.Drawing.Bitmap`。呼叫端的 `Bitmap bitmap = new Bitmap(...)` 必須改為 `Image image = Image.Load(...)`。

**修復方式 — 派單時必附 cascade 清單**：
```
注意：BitmapBase64_Funs.cs 的 API 簽名已改為 SixLabors.ImageSharp.Image，
所有呼叫端（CS_PrintTemplate:2253, orders_new:790, Login.axaml:242）必須一併修改。
變數宣告從 Bitmap → Image，new Bitmap(path) → Image.Load(path)。
```

**派單時必附提醒**: "先 grep 所有呼叫端檔案，確認哪些地方使用了舊版 Bitmap API，然後一併修改。不要只改工具類不改呼叫端。"

### 陷阱24: using 移除太徹底 — 未檢查實際 type usage (TASK-019 cascade fix)
**問題**: vpos_core 將 `using System.Drawing.Printing;` 從 EzioDll.cs 和 DeviceEdit.axaml.cs 移除，因為 namespace-level grep 沒有看到 `System.Drawing.Printing.` 前綴。但檔案內實際使用了 `PrinterSettings.InstalledPrinters`（無命名空間前綴，靠 using 解析）。

**根因**: 子代理的「unused using」檢查邏輯是 grep `using System.Drawing.*;` 然後看檔案內是否有 `System.Drawing.XXX.` 前綴。但 C# 中 if the type is referenced without namespace prefix (e.g. `PrinterSettings.InstalledPrinters`), the compiler resolves it via the using directive — so removing the using breaks compilation even though no fully-qualified reference exists in the code.

**修復方式**:
1. **移除 using 前，先 grep 檔案內是否有該 type 的簡寫引用**（無命名空間前綴）：
   ```bash
   # 檢查 PrinterSettings 是否被使用（無 System.Drawing.Printing. 前綴）
   grep -n "PrinterSettings\." VPOS_Avalonia/ToolLib/EzioDll.cs
   # 結果: L645: foreach (String PrinterName in PrinterSettings.InstalledPrinters)
   ```
2. **若找到簡寫引用 → 保留 using**，不要刪除。

**派單時必附提醒**: "移除 unused using 前，務必 grep 檔案內是否有該 type 的簡寫引用（無命名空間前綴）。例如 PrinterSettings.InstalledPrinters、Console.WriteLine 等 — 這些靠 using 解析，不能刪。"

### 陷阱25: CS1656 — using var 宣告的變數是只讀的 (TASK-019 cascade fix)
**問題**: C# 8+ `using var x = new(...)` 宣告的變數是只讀的（readonly），不可重新指派。若需要 Dispose 但又要動態建立實例，會觸發 CS1656。

**範例（TASK-019）**:
```csharp
// ❌ CS1656 — using var 宣告後無法重新指派
using System.Drawing.Bitmap bmpForDraw = new(...);
bmpForDraw = new System.Drawing.Bitmap(tempStream);  // ❌ CS1656
```

**修復方式**：拆開宣告與 using block：
```csharp
// ✅ 先宣告一般變數（不含 using）
System.Drawing.Bitmap bmpForDraw = null!;
using (var tempStream = new MemoryStream())
{
    imgSharp.Save(tempStream, new BmpEncoder());
    tempStream.Position = 0;
    bmpForDraw = new System.Drawing.Bitmap(tempStream);  // ✅ 可重新指派
}
using (bmpForDraw)
{
    g.DrawImage(bmpForDraw, ...);  // using block 確保 Dispose
}
```

**派單時必附提醒**: "若變數需要重新指派或動態建立實例，不要用 `using var` 宣告。改用 `var x = null!;` 宣告 + `using (x) { ... }` block 包裹 Dispose。"

## Lead 角色鐵律 (TASK-014-A1 使用者 2026-08-19 嚴重糾正)

### 陷阱26: Lead 不可自己動手改 code (角色錯位 — 最嚴重的流程違規)
**問題**: QA 發現 P0 問題時，vpos_lead 沒有退回開發者（vpos_core/vpos_ui），而是自己用 `patch` 直接修改。

**根因**: Lead 把自己從「Team Leader」降級成「資深工程師」，親自下場修 bug。這導致：
1. **下屬失去訓練機會**：`vpos_core` 沒有修正 P0 問題，失去學習與成長機會。
2. **流程斷裂**：任務狀態沒有正確從 `REVIEW` → `REJECTED` → 退回開發者 → 重修 → 重新 QA。
3. **失去 QA 閉環**：Lead 自己改完後，沒有再送回 QA 複查，直接改 QA 報告為 PASS。

**強制規範**：
- **❌ 禁止**：QA 發現問題時，vpos_lead 用 `patch`/`write_file`/`execute_code` 直接修改程式碼。
- **❌ 禁止**：vpos_lead 在 task_board.json 中把狀態從 `REVIEW` 直接跳到 `DONE`，跳過開發者重修。
- **✅ 強制**：QA 發現問題 → 標記 `REJECTED` → 退回開發者（vpos_core/vpos_ui）重修 → 開發者完成後 → 重新指派 QA 複查 → QA PASS → 標記 `DONE`。

**每輪開頭檢查**：若發現 task_board.json 中某任務從 `REVIEW` 跳到 `DONE` 而沒有經過開發者重修，立即補發修正任務給對應下屬。

**派單時必附提醒**: "QA 發現問題時，Lead 不可自己動手改 code。必須退回開發者重修，並重新指派 QA 複查。這是角色錯位，嚴重違規。"

### 陷阱27: Lead 不可修改 QA 報告 (球員兼裁判 — 最嚴重的流程違規)
**問題**: vpos_lead 在修正 P0 問題後，自己修改 QA 報告（review-reports/review-TASK-XXX.md），把狀態從 `Conditional Pass` 改為 `PASS`。

**根因**: Lead 既是「球員」（改 code）又是「裁判」（改 QA 報告）。QA 報告的客觀性被完全破壞。

**強制規範**：
- **❌ 禁止**：vpos_lead 或任何開發者修改 `review-reports/review-TASK-XXX-*.md`。
- **❌ 禁止**：vpos_lead 在 QA 報告中寫「已修復」或「PASS」，除非是 QA 複查後的結果。
- **✅ 強制**：QA 報告只能由 `vpos_qa` 修改。Lead 的職責是「確認 QA 報告的內容」，而不是「修改 QA 報告」。

**正確流程**：
1. Lead 修正 code → 通知 QA 進行「修正後驗證 (Re-verification)」。
2. QA 驗證通過 → QA 更新報告為 `PASS`。
3. Lead 根據 QA 報告更新 task_board.json → `DONE`。

**每輪開頭檢查**：若發現 QA 報告中有 Lead 的修改痕跡（非 vpos_qa 產出），立即通知使用者並重新指派 QA 複查。

**派單時必附提醒**: "QA 報告只能由 vpos_qa 修改。Lead 不可碰 QA 報告，不可跳過 QA 複查。球員兼裁判是嚴重違規。"

### 陷阱29: 子代理依賴派單提供的檔案清單，未自行 grep 全目錄掃描 → 遺漏檔案 (TASK-014-A2 教訓)
**問題**: vpos_core 在 TASK-014-A2a 中只處理了派單時提供的 12 個檔案清單，遺漏了另外 9 個檔案（ClosingHandover、DiDiEats、DiDiEats_OrderInfo、Loading、Login、ModifyCart、QrorderDetail 完全未處理，TakeawaysDetail 半完成，MainWindow 存根未刪除）。

**根因**: 子代理收到一份「已分析好的檔案清單」後，將其視為完整範圍，沒有自行執行 `grep -r 'MainWindow\\.m_dblZoom' VPOS_Avalonia/Views/` 來驗證是否還有遺漏。子代理的認知負載被派單的預載 context 綁定，形成「管窺效應」。

**修復方式 — 派單時必附「全目錄掃描」指令**：
```
⚠️ 注意：本任務涉及全專案 cascade 替換。
派單提供的檔案清單可能不完整。
完成後必須執行 `grep -r 'MainWindow\\.m_dblZoom' VPOS_Avalonia/Views/ | wc -l` 確認全目錄已無殘留，
而不是只檢查派單清單中的檔案。
```

**修復方式 — 子代理執行時必附「全目錄驗證」**：
1. 先對全 Views 目錄執行 `grep -r 'MainWindow\\.m_dblZoom' VPOS_Avalonia/Views/` 取得完整清單
2. 對清單中的**每一個**檔案執行替換（不只是派單提供的清單）
3. 最後再次 grep 確認殘留為 0

**派單時必附提醒**: "本任務是 cascade 替換，派單提供的檔案清單可能不完整。請先 grep 全 Views 目錄取得完整清單，對所有檔案執行替換，最後再 grep 確認殘留為 0。不要只處理派單清單中的檔案。"

**vpos_lead 派單檢查清單**:
- [ ] 派單時是否要求子代理先 grep 全目錄取得完整檔案清單？
- [ ] 若涉及 >10 個檔案的 cascade，是否在 goal 中明確寫「請先 grep 全目錄掃描」？
- [ ] Definition of Done 是否包含「全目錄 grep 殘留為 0」的驗證？

### 陷阱30: Cascade 替換後必須刪除代理屬性存根（遺漏刪除 = 編譯錯誤）
**問題**: 即使所有引用都已替換，若未刪除 MainWindow.axaml.cs 中的代理屬性存根（如 m_dblZoom、m_dblnum），會導致：
1. 編譯警告（Dead code）
2. 若未來有人誤用 `MainWindow.m_dblZoom` 會得到錯誤的運行時行為（因為存根仍在，只是指向 MainWindowState）
3. 違反 MVVM 解耦目標（存根仍是 Code-Behind 的 public static 暴露）

**修復方式**: 
1. 先完成所有引用替換
2. 再 grep 確認 `public static double m_dblZoom` 等存根宣告行號
3. 刪除整段存根（包含 getter/setter 和空行）
4. 最後 grep 確認存根宣告已不存在

**派單時必附提醒**: "完成所有引用替換後，必須刪除 MainWindow.axaml.cs 中的代理屬性存根宣告。最後 grep 確認 `public static` 宣告已不存在。"

### 陷阱32: Cascade 類型替換可能需新增 using 宣告（TASK-014-A2 編譯錯誤教訓）
**問題**: 將 `MainWindow.m_dblZoom` 替換為 `MainWindowState.Instance.mDblZoom` 後，SysBasic.axaml.cs 和 SysInvoice.axaml.cs 編譯錯誤 CS0103「名稱 'MainWindowState' 不存在於目前的內容中」。

**根因**: `MainWindow` 定義在 `VPOS_Avalonia.Views` namespace，而 `MainWindowState` 定義在 `VPOS_Avalonia.ViewModels` namespace。替換前檔案已有 `using VPOS_Avalonia.Views;`（可解析 MainWindow），但替換後需要 `using VPOS_Avalonia.ViewModels;`（可解析 MainWindowState），而這些檔案沒有這個 using。

**處理流程**：
1. **vpos_lead 派單前**：對所有受影響的檔案執行 `head -20 <file>` 檢查是否已有 `using VPOS_Avalonia.ViewModels;`
2. **有 using 的檔案**：只需做 replace
3. **沒有 using 的檔案**：在 replace 之前先 patch 加入 using
4. **委派時**：將需要加 using 的檔案清單明確列出，並要求子代理在替換後驗證 using 存在

**派單時必附提醒**: "注意：`MainWindowState` 定義在 `VPOS_Avalonia.ViewModels` namespace。請先 grep 所有受影響檔案，檢查是否有 `using VPOS_Avalonia.ViewModels;`。若沒有，必須先 patch 加入 using，再做 replace。完成後驗證所有檔案都有此 using。"

**vpos_lead 直接 patch 的 using 補齊模式**:
若 vpos_lead 發現有檔案缺少 using，在 replace 之前先 patch：
```csharp
// 在 using VPOS; 之後加入
using VPOS_Avalonia.ViewModels;
```

### 陷阱33: vpos_lead 派單前必須先 grep 全目錄取得完整清單（強化陷阱 29）
**問題**: vpos_lead 在分析任務時，只grep了部分檔案或只看了子代理的輸出，沒有自己先執行全目錄掃描就派單。導致子代理拿到不完整清單。

**根因**: vpos_lead 過度信任派單 context 中的檔案清單，沒有自行驗證完整性。

**強制規範**：
- **❌ 禁止**：不 grep 全目錄就派單 cascade 任務。
- **✅ 強制**：每次委派涉及多檔案替換的任務前，**必須先執行** `grep -r '舊模式' VPOS_Avalonia/Views/` 取得完整清單。
- **✅ 強制**：將完整清單（不只是部分清單）放入 delegation context 的 goal 欄位。
- **✅ 強制**：若 grep 結果顯示 >15 個檔案，考慮拆成多個 subtask（避免子代理認知負載過高）。

**每輪開頭檢查**：若上一輪有 cascade 任務但 vpos_lead 沒有先 grep 全目錄，這輪開頭立即補上全目錄 grep 並更新派單。

**回應格式**：
每次委派 cascade 任務前，在回應中**必須包含以下行**：
```
🔍 全目錄掃描結果: grep -r '舊模式' VPOS_Avalonia/Views/ → N 個檔案, M 處引用
```

如果因為某種原因沒做全目錄掃描（例如使用者要求先分析再派單），在回應中明確標註：
```
⚠️ 全目錄掃描待執行（等確認後再 grep）
```

**派單時必附提醒**: "委派 cascade 任務前，必須先 grep 全目錄取得完整檔案清單。不要依賴子代理或預載 context 中的部分清單。"

### 陷阱34: 分析任務時必須優先使用 graphify 而非 grep（2026-08-19 使用者糾正）
**問題**: vpos_lead 在分析任務時，直接使用 grep 全文搜尋來確認關聯，而不是使用 graphify 技能來查詢模組依賴關係。
- grep 是「看到什麼改什麼」的暴力方式，會遺漏非靜態引用（如直接欄位存取 `m_XXX`）
- graphify 是「理解依賴關係」的結構化方式，會列出所有檔案 + 行號 + 引用方式
- 這導致 TASK-014-A3 遺漏了 MainWindow.axaml.cs 內部的直接欄位引用（4 處），QA REJECTED

**強制規範**：
- **❌ 禁止**：分析任務時只使用 grep 全文搜尋（grep 僅用於最終驗證，不用於分析）
- **✅ 強制**：分析任務時必須先執行 `graphify query "<符號>"` 查詢
- **✅ 強制**：若 graphify 查詢無結果，改用 `graphify query "<符號> 引用"` 或 `graphify query "<檔案> 依賴"`
- **✅ 強制**：若 graphify 查詢結果超過 20 個檔案，考慮拆成多個 subtask
- **✅ 強制**：grep 僅用於「確認 graphify 分析結果」的最終驗證步驟

**每輪開頭檢查**：若上一輪分析任務時沒有使用 graphify，這輪開頭立即補上 graphify 查詢。

**回應格式**：
每次分析任務時，在回應中**必須包含以下行**：
```
🔍 Graphify 查詢: graphify query "<符號>" → N 個檔案, M 處引用 (包含靜態 + 直接欄位)
```

如果因為某種原因沒做 graphify 查詢（例如使用者要求先分析再派單），在回應中明確標註：
```
⚠️ Graphify 查詢待執行（等確認後再查詢）
```

**派單時必附提醒**：「分析任務前，必須先使用 graphify 查詢模組依賴關係，確認所有引用方式（靜態 + 直接欄位）。不要只靠 grep 全文搜尋。」

### 陷阱36: 內部直接屬性引用（非 MainWindow.m_xxx 格式）— proxy 刪除陷阱（2026-08-20 新增）
**問題**: MainWindow.axaml.cs 中的方法內部（如 takeaways_params2Var()）使用 `m_StrPosExpenseNumber = ""`（直接屬性存取），而非 `MainWindow.m_StrPosExpenseNumber`。當刪除 proxy property 存根時，這些內部直接引用會斷裂。

**根因**: 代理屬性存根在 MainWindow.axaml.cs 內部被視為「同一類別的 static member」，所以方法內直接寫 `m_xxx = value` 即可。但一旦刪除存根，這些引用就找不到定義了。

**修復方式**：
1. 分析 proxy property 時，**必須同時 grep 兩種模式**：
   - `grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/` — 外部檔案引用
   - `grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs` — 內部直接賦值
   - `grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs` — 內部直接讀取
2. 全部替換為 `MainWindowState.Instance.mXxx`
3. 最後才刪除存根

**派單時必附提醒**: "注意：MainWindow.axaml.cs 內部方法可能使用直接屬性存取（如 `m_xxx = value`），不只是 `MainWindow.m_xxx`。請 grep 全 MainWindow.axaml.cs 確認所有引用模式。"

### 陷阱37: 子代理 DoD 計數不可靠 — 必須獨立 grep 驗證（2026-08-20 新增）
**問題**: vpos_core 回報 TASK-014-A6 的 DoD 計數為 5 處 mStrPosExpenseNumber（4 internal + 1 external）和 8 處 mStrPosReportNumber（6 internal + 2 external），但任務書面列出的是 10 處內部引用 + 3 處外部引用。實際執行結果與書面不一致。

**根因**: 子代理在派單 context 中收到「應有 10 處內部引用」的預期值，但在實際 grep 時可能計數錯誤或只檢查派單清單中的檔案。

**修復方式**：
1. **vpos_lead 必須獨立執行 grep 驗證**，不依賴子代理的回報數字
2. 子代理完成後，vpos_lead 執行 `grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs' | wc -l` 取得獨立計數
3. 若子代理計數與獨立驗證不一致 → 標記為需要二次確認，不直接標記 DONE

**派單時必附提醒**: "完成後請獨立執行 grep 驗證，不要依賴派單 context 中的預期計數。"

### 陷阱38: 存根刪除前必須完成所有引用替換（含內部直接存取）（2026-08-20 新增）
**問題**: 若先刪除 proxy property 存根，再處理內部直接引用，會導致編譯錯誤。TASK-014-A5f 中 m_UBER_EATS_params 和 m_FOODPANDA_params 的存根被刪除後，takeaways_params2Var() 中的 `m_UBER_EATS_params = ...` 直接賦值變成 CS0103。

**根因**: 子代理先完成了外部引用替換，但忘了處理 MainWindow.axaml.cs 內部的直接存取，然後就刪除了存根。

**修復順序（鐵律）**：
1. **Step 1**: 外部檔案 cascade 替換（所有 Views/, WebAPI/, Thread/ 等）
2. **Step 2**: MainWindow.axaml.cs 內部引用替換（含 `m_xxx =`、`m_xxx.`、`m_xxx ==` 等所有模式）
3. **Step 3**: 獨立 grep 驗證 — `grep 'MainWindow\\.m_xxx'` 應為 0，`grep 'm_xxx =\\|m_xxx \\.'` 應改為 `MainWindowState.Instance.mXxx`
4. **Step 4**: 刪除存根
5. **Step 5**: 最終驗證 — `grep 'public static.*m_xxx'` 應為 0

**派單時必附提醒**: "嚴格遵守順序：(1) 外部 cascade → (2) 內部直接存取 → (3) 獨立驗證 → (4) 刪除存根 → (5) 最終驗證。不可跳過任何步驟。"

### 陷阱35: 子代理完成後必須立即推進，不可等待 Cron（2026-08-19 使用者糾正）
**問題**: vpos_lead 在 dispatch 子代理後，沒有主動檢查子代理狀態，而是等待 Cron watchdog 定時檢查。
- Cron 是「防呆機制」，不是「主要溝通管道」
- 子代理完成時，系統會送 ASYNC DELEGATION COMPLETE 通知，但 vpos_lead 沒有在第一時間回應
- 這導致 TASK-014-A3 的修正常等了 15 分鐘才推進

**強制規範**：
- **❌ 禁止**：dispatch 後不檢查子代理狀態，等待 Cron
- **✅ 強制**：收到 ASYNC DELEGATION COMPLETE 通知後，**立即**檢查子代理結果
- **✅ 強制**：若子代理完成，**立即**進行下一步（更新任務板 + 派 QA），不要等 Cron
- **✅ 強制**：dispatch 後 5 分鐘內必須主動檢查 `delegate_task(action='list')` 確認狀態
- **✅ 強制**：每輪開頭必須檢查是否有 pending 的 delegate_task

**每輪開頭檢查**：若上一輪有 `delegate_task` 但沒有檢查子代理狀態，這輪開頭立即檢查。

**回應格式**：
每次 `delegate_task` 完成後，在回應中**必須包含以下行**：
```
✅ delegate_task 已派出 (delegation_id: deleg_XXXXX)
📋 已建立 Cron watchdog (job_id: XXXXX, schedule: every 3m)
⏰ 5 分鐘後將主動檢查子代理狀態
```

若子代理完成，**立即**在回應中回報：
```
✅ 子代理已完成 (delegation_id: deleg_XXXXX)
📋 下一步：更新任務板 + 派 QA
```

**派單時必附提醒**：「dispatch 後 5 分鐘內必須主動檢查子代理狀態，不可等待 Cron。子代理完成時必須立即推進下一步。」

## 開發約束條款 (派單時必附)
> ⚠️ **VPOS 專案開發與架構約束：**
> 1. 嚴禁在 Code-Behind (.axaml.cs) 中編寫商業邏輯，UI 邏輯必須透過 CommunityToolkit.Mvvm 綁定至 ViewModel[cite: 5]。
> 2. 所有非同步/背景作業必須注意 UI 執行緒切換（`Dispatcher.UIThread.InvokeAsync`）[cite: 5]。
> 3. 硬體 (WinAPI) 與 WebAPI 通訊必須包含異常捕捉與 Retry 機制，嚴禁阻塞 UI 主執行緒[cite: 5]。
> 4. SQL 查詢必須使用 Dapper 參數化 (`@param`)，嚴禁 `string.Format` 拼接 SQL[cite: 5]。

## 任務追溯機制 (修改既有功能時必查)
1. **Graphify 查詢**: `graphify query "<功能名稱> 建立日期 相關檔案"` 找出模組邊界[cite: 5]。
2. **任務板搜尋**: 在 `docs/` 搜尋 task_board，檢查是否有任務涉及該功能檔案[cite: 5]。
   - 有 → 追溯原始需求背景[cite: 5]
   - 無 → 以黑盒方式處理，不假設業務邏輯[cite: 5]
3. **Git Blame**: `git blame <檔案>` 確認最後修改者[cite: 5]。

## System.Drawing → ImageSharp Migration (references/system-drawing-to-imagesharp-migration.md)
- 完整遷移指南：`references/system-drawing-to-imagesharp-migration.md`
- 包含 7 種分類（unused using、Bitmap.Load、Save encoder、Base64 重構、ZXing hybrid、DPI 保留、NuGet 移除）
- API 差異對照表與驗證檢查清單

## Ad-hoc Verification Script Pattern (TASK-015)
**問題**: C# 編譯錯誤修復後，需要快速驗證所有 patch 是否正確應用。

**做法**: 寫一個 `/tmp/hermes-verify-cs0122-fix.sh` 腳本：
1. grep 確認 using 語句存在（MainWindowState.cs）
2. grep 確認 internal 宣告存在且 private 宣告為 0（MainWindow.axaml.cs）
3. 輸出 PASS/FAIL 統計

**執行**: `bash /tmp/hermes-verify-cs0122-fix.sh` → 確認全部 PASS → rm -f 清理。

**適用場景**: 
- ✅ vpos_lead 直接 patch 後的快速驗證（grep count）
- ❌ delegate_task 完成後不需要 — 子代理已附帶 ls -la + grep 驗證結果
- ⚠️ 不要為每個小 patch 都寫腳本，簡單 grep 即可

## 全新環境初始化檢查清單 (2026-08-19 新增)

當接手全新環境或長時間未執行任務時，依序檢查：

### Step 0: 環境與目錄
- [ ] 確認 `/media/sf_VPOS_Avalonia` 目錄存在且可寫入
- [ ] 確認 `docs/`、`review-reports/`、`FlaUI_Test/`、`NSIS_Project/` 目錄存在
- [ ] 確認 `task_board.json` 已初始化（若無則建立空結構）

### Step 1: Profile 驗證
- [ ] 測試 `hermes chat -q "hello" --profile vpos_core --cli`（確認實體啟動）
- [ ] 確認三個 SOUL.md 的目錄邊界正確（vpos_core 不碰 Views/、vpos_ui 不碰 DBLib/）

### Step 2: Cron 清理
- [ ] `cronjob action=list` → 清除所有舊任務（保留 `VPOS Patch Notify Watchdog`）

### Step 3: 工具準備
- [ ] 確認 `monitor_subagent.py` 存在於 `/home/vblinux/.hermes/profiles/vpos_lead/scripts/`
- [ ] 確認 `skill_view('vpos-delegation-workflow')` 可載入無 [SKILL_PRUNED]

## Definition of Done（DoD）實體寫入驗證 — 鐵律（2026-09-21 借鏡 jl-delegation-workflow，收散落的陷阱）

子代理回報完成後，**必須獨立驗證，不可信任其自報數字**（vpos 教訓：子代理 DoD 計數常與實際不符）。依任務性質執行對應項目：

1. **檔案痕跡**: `ls -la <target_file>` — 比對修改時間與大小是否為最新。
2. **實質內容 grep**: 例如 `grep -c "GetSharedConnection().Query" <檔案>`、`grep -rn "MainWindowState.Instance.mXxx" VPOS_Avalonia/Views/`，確認修復點數與預期一致（不是 grep 類別名，是 grep `new Xxx(` 等實質模式）。
3. **全目錄殘留**: cascade 替換任務必須 `grep -r '舊模式' VPOS_Avalonia/ --include='*.cs' | wc -l` → 應為 0，**不是只檢查派單清單中的檔案**。
4. **存根刪除確認**: proxy property 刪除後 `grep 'public static.*m_xxx'` 應為 0。
5. **編譯驗證（最終）**: `dotnet build -c Release` — 但注意 .NET SDK 不可用時由使用者驗收，vpos_lead 只做 grep 層級驗證。

> ⚠️ DoD 計數不可靠 — 子代理回報的修改處數常與實際不符，lead 必須自己 grep 核對後才更新 task_board.json。

## 跨人格技能／記憶分發（VPOS 版）

當我在 lead 端**新增或更新委派/審查類 skill**、或把教訓寫進各 persona MEMORY.md 時，必須按工作範圍同步到對應下屬 profile。

### 關鍵事實：profile skills 是「複製」非 symlink；global skills 自動共用
- **profile `skills/`**（vpos_lead / vpos_core / vpos_ui / vpos_qa）是**獨立副本**，不是連結。在 lead 新增 skill **不會**自動出現在下屬。必須手動 `cp -r` 分發，並用 `ls` 驗證。
- **global `skills/`**（`~/.hermes/skills/`）所有 profile **自動共用、零摩擦**。換專案（新工作目錄）也照載——技能存在 profile/global 層級，不在專案目錄（如 `VPOS_Avalonia/`），故與專案解耦。

### 分發矩陣（按下屬工作範圍）
| 技能／記憶類別 | lead | core | ui | qa |
|---|---|---|---|---|
| 委派／QA 流程類（vpos-delegation-workflow、refactoring-qa-review） | Y | **Y** | **Y** | **Y** |
| DB/硬體/API 專屬（sql-injection、connection-pooling、concurrency-audit） | Y | **Y** | N（無此範圍） | **Y** |
| UI 專屬（proxy-property-cleanup、extract-static-to-singleton） | Y | N | **Y** | **Y** |
| MEMORY.md 教訓 | 寫入對應職責段落 | DB/硬體根因+修復 | UI 重構教訓 | QA 審查重點 |

### 分發後驗證（必做）
```bash
for s in vpos-delegation-workflow refactoring-qa-review; do printf "%-38s core=%s ui=%s qa=%s\n" "$s" \
  "$( [ -d /home/vblinux/.hermes/profiles/vpos_core/skills/$s ] && echo Y || echo N )" \
  "$( [ -d /home/vblinux/.hermes/profiles/vpos_ui/skills/$s ] && echo Y || echo N )" \
  "$( [ -d /home/vblinux/.hermes/profiles/vpos_qa/skills/$s ] && echo Y || echo N )"; done
```
委派/QA 流程類 → core+ui+qa（三屬全發）。分發後務必 `ls` 確認存在，再執行 Hermes_BK 備份。

## 多執行緒修補與 QA 交付陷阱 (TASK-031~033)

### 陷阱41: CRLF↔LF 行尾混淆地獄（TASK-033 教訓）
**問題**: vpos_core 用 patch/write_file 寫入 .cs 後，可能把整檔從 CRLF 轉成 LF → `git diff --stat` 顯示「539 insertions / 539 deletions」全檔異動。子代理嚇到，瘋狂用 sed/python 還原 CRLF：(a) `sed -i 's/$/\r/'` 會把已 CRLF 的行變成 CR+CR（行尾翻倍），(b) `git checkout` 會把實際修改也還回去，(c) 內容一度翻倍到 1078 行。最後卡死 16+ 分鐘。
**根因**: 子代理把「行尾轉換的 cosmetic diff」當成「實質錯誤」來修，越修越糟。
**修正（派單時必附）**:
- `git diff --stat` 顯示全檔異動 = 99% 是 CRLF↔LF 行尾噪音，不是真改錯。**用 `git diff`（看實質內容）+ python 檢查確認無損毀即可**：
  ```bash
  git --no-pager diff <檔案>            # 實質內容只有一行變更 = DONE
  python3 -c "d=open('<檔案>','rb').read(); print('null:',d.count(b'\x00'),'CRLF:',d.count(b'\r\n'))"  # 無 null bytes、行數未翻倍
  ```
- **不要**讓子代理去「還原 CRLF」。只要 git diff 實質內容符合預期就過。
- 若真的要統一行尾，用 python binary mode（先全轉 LF 再全轉 CRLF），絕不用 `sed 's/$/\r/'`：
  ```python
  d=open(f,'rb').read(); d=d.replace(b'\r\n',b'\n').replace(b'\r',b'\n').replace(b'\n',b'\r\n'); open(f,'wb').write(d)
  ```

### 陷阱42: vpos_qa delegate_task 完成審查卻不寫報告檔（TASK-033 教訓）
**問題**: vpos_qa 子代理連續三次完成 QA 審查、給出合理 PASS verdict，但每次都沒把報告寫入 `review-reports/`。它以為「回覆 verdict JSON」就是完成，實際漏了 write_file + ls 確認。
**根因**: 子代理對「完成」的定義與 DoD 不符——產出了結論但沒產生交付物（報告檔）。
**修正**:
- 派 vpos_qa 時 DoD 明確寫入：「完成 = 用 write_file 把報告寫入 `review-reports/review-TASK-XXX-*.md`，並用 `ls -la` 確認檔案存在」。只回 JSON verdict 不算完成。
- 子代理回報 completed 後，vpos_lead **必須** `ls review-reports/ | grep TASK-XXX` 獨立確認報告檔存在。不存在 = 未完成。
- 連續 2 次（約 7~9 分鐘）仍不寫 → vpos_lead 接管：用 git diff 實質內容 + 一致的 verdict，手動撰寫報告並標 DONE。**code 是下屬改的、報告只是記錄已驗證事實 ≠ 球員兼裁判**（陷阱26/27）。

### 陷阱43: cron watchdog 誤用 delegate_task 第二項建立（TASK-033 教訓）
**問題**: 需要「dev 子代理 + cron watchdog」時，把兩者當成 `delegate_task(tasks=[...])` 的兩個項目並行送出。第二個 item（「建立 TASK-XXX 的 cron watchdog」**不是真正的 cron**——它變成一個假的、被立即停止的子代理，因為 cron watchdog 必須用獨立的 `cronjob_manage(action='create')` 建立，不是 delegate_task）。後果：(a) 多派一個無意義子代理要回頭 stop；(b) 容易誤以為 watchdog 已建而漏掉真正的 cron。
**根因**: 混淆了「委派子代理」（`delegate_task`）與「排程 cron」（`cronjob_manage`）兩個不同工具，把後者塞進前者的 fan-out。
**修正（鐵律）**:
- `delegate_task(tasks=[...])` 的每個 item **都是「一個子代理」**。若同一輪需要 dev + watchdog，用**一次 delegate_task（只放 dev goal）**＋**一次獨立的 cronjob_manage(action='create')**。兩者分開呼叫，絕不塞進同一個 fan-out。
- 送出後回應必報兩個不同來源的 ID：`✅ delegate_task delegation_id: deleg_XXXXX` ＋ `📋 Cron watchdog job_id: XXXXX, schedule: every 3m`。任一缺失 = 漏建。
- 每輪開頭若發現有 delegate_task 卻沒有對應 cron job_id，立即補建（陷阱22/40）。

### 陷阱44: 委派週期收尾漏跑 watchdog 統一檢查（TASK-034 教訓）
**問題**: 陷阱43 會製造明顯的結構異常（一個 delegation_id 卻有兩個 goal），當場就能自我察覺。但「QA/dev 任務太小、完全沒建 watchdog」是另一種失敗模式——它**沒有任何紅燈訊號**：任務小而快，跑完直接回傳 PASS，Lead 順手就進 board 或通知使用者，根本沒有東西在當下提醒去建 watchdog。陷阱22/40 的「零豁免」規則明明寫了，卻剛好斷裂在這個無訊號盲區。
**根因**: 「漏建 watchdog」不會產生即時失敗；它只在任務完成後才顯現為 orphan（active delegation 沒有對應 cron）。所以不能靠「出錯當下自我察覺」，必須在收尾時做一個與任務快慢無關的結構性檢查。
**修正（鐵律 — 委派週期收尾檢查）**：
- **每輪結束、在宣告完成或通知使用者編譯驗收之前**，一律先跑一次 `cronjob action=list`，執行以下對帳：
  1. 列出所有 active delegation（delegate_task action=list）。
  2. 每個 active delegation 都必須有且僅有一個 watchdog job_id。
  3. 已完成的任務，其 watchdog 必須已被移除（remove）；若還在 = orphan，立即 remove。
- 這條檢查跟「任務大小/快慢」完全無關——它抓的是結構一致性，不是執行品質。即使只派了 6 分鐘的 QA 小任務，收尾照跑。
- **回應格式**：每輪委派週期結束時，在回應中明確標註 watchdog 對帳結果：
  ```
  📋 Cron watchdog 對帳: active delegations=0, orphan jobs=0 ✅（TASK-034 watchdog 7b44d201a691 已移除）
  ```
  若發現 orphan → 立即 `cronjob action='remove'`，再標註已清理。
- **每輪開頭也檢查**：若上輪有委派但回應裡沒有 watchdog 對帳行，這輪開頭立即補跑 `cronjob action=list` 並對帳。

### 陷阱45: task_board.json / 流程檔更新後未做 JSON 驗證 + 未備份（流程紀律缺口，2026-09-22 借鏡 jl-delegation-workflow 陷阱19）
**問題**: 子代理或 lead 改完 `task_board.json`、`issue-log.md` 等流程檔後直接跳下一步，沒有執行 JSON 語法驗證；若 JSON 壞掉，後續所有讀取 task_board 的邏輯（含防重工檢查）全部失效且難以察覺。
**根因**: 「更新 task_board」被當成機械動作，忽略了「它也是會被程式解析的資料檔」。
**修正（Lead 必守）**：
- **每次寫入 `task_board.json`（Phase 1 建立 / Phase 2 REVIEW / Phase 3 DONE）後，必須立即執行 JSON 驗證**：
  ```bash
  python3 -c "import json;json.load(open('docs/task_board.json'));print('JSON OK')"
  ```
- 驗證通過才算完成該步；壞掉 → 用 `write_file` 重寫成合法結構，不得帶著坏檔進入 QA。
- **流程紀律**：task_board / issue-log 這類「被程式讀取的資料檔」**是專案可重生成物，更新後不觸發 Hermes_BK 備份**（依 0.5 備份觸發鐵律）。
- 派單時必附提醒：「改完 `docs/task_board.json` 後必須 `python3 -c \"import json;json.load(open('docs/task_board.json'))\"` 驗證，壞檔不得進入 QA。」

> ⚠️ 與既有規則的關係：陷阱17（sibling JSON patch）補的是並發情境的寫入安全；陷阱45 補的是「寫完沒驗證」的流程紀律缺口。兩者互補。task_board/issue-log 是專案檔，更新後不觸發 Hermes_BK 備份（依 0.5 備份觸發鐵律）。

### 陷阱46: 盲目信任委派回傳的 status 字串，未查 disk artifact（TASK-037 G3 Part A QA 教訓, 2026-09-23）
**問題**: vpos_lead 收到子代理 `status=failed`（context window overflow）與 `status=blocked`（output_schema 為空），據此斷言「QA 審查連續失敗兩次、沒有任何成果」，並準備自己重寫一份品質較差的報告。實際上第 2 輪子代理在 context overflow **之前**已把完整的 80 行 QA 報告寫入 `review-reports/review-TASK-037-printthread-partA.md`（後來 write_file 因檔案已存在而拒絕覆寫，才揭露真相）。
**根因**: 把「委派回傳的狀態字串」當成「成果是否存在」的權威來源。狀態字串只是線索（line clue），disk 上的實際 artifact（報告檔、git diff、transcript）才是事實（fact）。子代理在 context overflow / blocked 前可能已寫入部分或全部交付物，直接放棄會遺失這些成果。
**修正（鐵律 — failed/blocked 後的第一動作）**：
- 任何委派回傳 `failed` / `blocked` / `incomplete` / 非預期狀態時，**第一時間先查 artifact，不要先下結論**：
  ```bash
  ls -la review-reports/ | grep TASK-XXX          # 報告檔是否已存在
  git --no-pager diff --stat <target_file>         # dev 檔案實質變更
  tail -50 <live_transcript_path>                  # transcript 最後痕跡
  ```
- 若 artifact 顯示成果已寫入（例如報告檔存在且內容完整），即使 status=failed，也**視為已完成**、直接推進下一步（更新 task_board + 通知驗收），不要重做或丟棄。
- 只有當 artifact 確認「真的沒有產出」時，才判定為需要重派/接管。
- **判斷順序**：artifact 存在且完整 → PASS；artifact 部分存在 → 視情況補強；artifact 完全不存在 → failed，重派。

> ⚠️ 與陷阱42的關聯：陷阱42抓「QA 完成審查卻不寫報告檔」（有結論沒交付物）；陷阱46抓相反面——「子代理已寫出交付物，但 Lead 因信任 status 字串而誤判為無成果」。兩者都強調：**以 disk artifact 為準，不以 status 字串為準**。

## 跨 Profile Skill 借鏡方法論（2026-09-22 借鏡 jl_lead，完整流程見 references/cross-profile-skill-borrowing.md）

審查其他 profile（jl_lead、jl_php…）的 skill 時，照該 reference 的流程做：挑出**跨領域通用的委派/QA/監控缺陷**整合進來，而非逐字複製。

- **通用 vs 語言專屬篩選準則**：根因依賴特定語言/框架/編譯器行為者（CS0122、ImageSharp、proxy cleanup…）刻意不搬；根因是「流程結構／工具誤用／認知偏差」者（watchdog orphan、dev→qa race、QA 不寫報告、cascade 管窺、CRLF cosmetic diff、JSON 未驗證備份、Gateway 常駐四項檢查）才借鏡。
- **工具移植三問**：(1) cache/輸入結構一致嗎？(2) 改良後更準嗎？(3) 硬編碼路徑要換 profile 嗎？結構一致 → cp + 換路徑；不同 → 改良後用真實 transcript 實測再入库。
- **已借鏡並落地**：jl_lead 的 `monitor_subagent.py`（vpos cache 結構與 jl 完全一致）→ 直接升級我的版本，新增 `--all` 全量列出 + manifest.json 權威判定（取代 grep final_response）。已用真實 transcript 實測通過。
- **借鏡後必做**：patch 自己的 SKILL.md → cp 到 global + vpos_core/vpos_ui/vpos_qa（md5 全驗）→ Hermes_BK 備份。

---
name: vpos-delegation-workflow
description: VPOS Avalonia 專案任務委派、監控與 QA 閉環標準作業程序
---

# VPOS Project Delegation Workflow

## 核心原則
1. **全面下放**: 除最終編譯打包外，所有開發與審查任務必須委派給對應下屬 (`vpos_core`, `vpos_ui`, `vpos_qa`)。
2. **強制監控**: 委派任務後，**必須**立即建立 Cron 排程（每 3 分鐘檢查，共 10 次）以防子代理卡死。
3. **閉環審查**: 下屬完成後，必須指派 `vpos_qa` 進行程式碼審查，未通過 QA 不得進入下一問題。
4. **等待指示**: 僅在 QA PASS 後通知使用者驗收。等待使用者明確指示後，才繼續下一個任務。

## 標準流程
0. **Graphify 圖譜維護與查詢 (任務前強制步驟)**:
   - 檢查 `graphify-out/GRAPH_REPORT.md` 最後修改時間。若超過 24 小時或涉及新檔案，執行增量更新：
     ```bash
     /graphify /media/sf_VPOS_Avalonia --update
     ```
   - 根據任務範圍執行 `graphify query "..."` 查詢相關模組依賴圖、呼叫鏈、community 邊界。
   - 將關鍵發現寫入 `review-reports/` 下的任務暫存檔，供子代理參考。

1. **問題分析 (雙軌制)**:
   - **軌道 A (現有問題修復)**: 閱讀 `review-reports/02_問題詳細說明與檔案對應表.md`，結合 graphify 查詢結果拆解為單一原子任務。
   - **軌道 B (全新開發項目)**: Graphify 全域探索 → 確認需求 → 建立 `docs/` 任務板 → 派單。

2. **任務委派**:
   - 後端/DB/硬體 → `vpos_core` (工作目錄: `DBLib/`, `WinAPI/`, `ToolLib/`, `Thread/`)
   - UI/AXAML/ViewModel → `vpos_ui` (工作目錄: `Views/`, `ViewModels/`, `UserControl/`)
   - **關鍵**: 委派時必須明確告知「工作目錄限制」與「開發約束條款」。

3. **建立監控**:
   - `cronjob(action='create')`，`schedule: every 3m`，`repeat: 10`
   - `prompt`: 檢查子代理狀態、檔案修改痕跡、回報進度或卡死。

4. **QA 審查**:
   - **子代理委派優先**: `hermes chat -q "..." --profile vpos_qa --cli --toolsets terminal,file`
   - **⚠️ CLI 委派限制**: 若 `-q` 超時 (>120s) 或 Unicode 錯誤，**vpos_lead 手動審查**。
   - **手動審查**: `read_file` → `grep -n` 確認 → 寫入 `review-reports/review-TASK-XXX-*.md` → 更新 task_board.json。

5. **通知使用者**: QA PASS 後通知使用者驗收，等待明確指示才繼續下一個任務。

## 開發約束條款 (派單時必附)
> ⚠️ **VPOS 專案開發與架構約束：**
> 1. 嚴禁在 Code-Behind (.axaml.cs) 中編寫商業邏輯，UI 邏輯必須透過 CommunityToolkit.Mvvm 綁定至 ViewModel。
> 2. 所有非同步/背景作業必須注意 UI 執行緒切換（`Dispatcher.UIThread.InvokeAsync`）。
> 3. 硬體 (WinAPI) 與 WebAPI 通訊必須包含異常捕捉與 Retry 機制，嚴禁阻塞 UI 主執行緒。
> 4. SQL 查詢必須使用 Dapper 參數化 (`@param`)，嚴禁 `string.Format` 拼接 SQL。

## 任務追溯機制 (修改既有功能時必查)
1. **Graphify 查詢**: `graphify query "<功能名稱> 建立日期 相關檔案"` 找出模組邊界。
2. **任務板搜尋**: 在 `docs/` 搜尋 task_board，檢查是否有任務涉及該功能檔案。
   - 有 → 追溯原始需求背景
   - 無 → 以黑盒方式處理，不假設業務邏輯
3. **Git Blame**: `git blame <檔案>` 確認最後修改者。

## 任務板格式規範
```yaml
---
task_board_name: <任務板名稱>
created_date: <YYYY-MM-DD>
task_type: new_feature | bug_fix | maintenance
created_by: vpos_lead
status: IN_PROGRESS | DONE
---
```
每個 Task 標註：id, title, type, assignee, status, files_affected, created_date, commit_hash。

## 決策矩陣 (2026-08-07 實戰驗證)

| 場景 | 執行者 | 原因 |
|------|--------|------|
| 單一檔案 ≤3 處修改 | vpos_core (委派) | subagent 不易迷失 |
| 單一檔案 >5 處修改 | vpos_lead (直接 patch) | subagent 易迷失，vpos_core 曾有兩次沒寫入檔案 |
| 三檔案同時修改 (≤3 處/檔案) | vpos_lead (同時 patch) | TASK-006 驗證：同時送交 3 個 patch 成功且高效 |
| QA 審查 | vpos_qa (委派) | 效果良好，產出完整報告 |
| 編譯/打包/混淆 | vpos_lead (直接執行) | 最終交付步驟 |

## 委派失敗防範機制
### 問題背景
`vpos_core` 被委派修改 `SqliteDataAccess.cs` 兩次，但兩次都沒有實際修改檔案。task_board 被錯誤標記為 REVIEW/DONE。

### 防範措施
1. **委派前**: 先 `read_file` 讀取目標檔案，在派單 context 附上「原始程式碼片段」與「修改後預期樣貌」。
2. **委派後 30 秒內**: `ls -la` 確認檔案時間戳記 + `grep -c` 確認修改字串存在。
3. **失敗處理**: 第一次失敗→重新委派；第二次失敗→vpos_lead 直接 patch。
4. **強制檢查清單** (派單 context 必加):
   ```
   ## 強制檢查清單 (完成前必做)
   1. 用 grep 確認目標字串已存在於檔案中。
   2. 用 ls -la 確認檔案時間戳記已更新。
   3. 用 grep 確認原始問題字串已不存在。
   4. 建立審查報告檔：review-reports/review-TASK-XXX-*.md
   5. 回覆時附上以上驗證結果。
   ```

## 加密演算法遷移策略 (TASK-005/006 教訓)
- **問題**: 修改加密模式（ECB → CBC/GCM）時，若呼叫方使用硬編碼密文，直接改演算法會導致所有密文無法解密。
- **正確策略（兩階段）**:
  - **Phase 1**: 僅將已淘汰類別替換為現代類別（`RijndaelManaged` → `Aes.Create()`），維持相同模式 + Padding。
  - **Phase 2**: 當金鑰也外置時，一併更改加密模式並重新加密所有密文。
- **關鍵檢查**: 修改加密前，先用 `grep -r "Cryption.AesEncrypt\|Cryption.AesDecrypt"` 找出所有呼叫方。

## 常見坑點與經驗教訓
- **Dapper Dynamic 問題**: `Query<dynamic>` 回傳 `DynamicRecord`，實作 `IDictionary<string, object>` 而非 Reflection 屬性。處理動態結果時必須先檢查 `is IDictionary<string, object>`。
- **CLI 委派限制**: `hermes --profile <name> "<任務內容>"` CLI 命令會被 shell 解析，特殊字元（`$`, `'`, `"`, `{`, `}`）會導致語法錯誤。正確做法是使用 `delegate_task(goal=..., context=..., role='leaf')` 委派。
- **QA 閉環不可跳過**: 修復 → 狀態改為 REVIEW → 派 QA → QA PASS → 狀態改為 DONE → 通知使用者 → 等待指示 → 才進行下一個任務。
- **QA 子代理報告 ≠ 實際產出**: 子代理回報「完成」不代表檔案已寫入。任務完成後必須用 `ls` 或 `find` 確認關鍵產出檔案確實存在。
- **驗證腳本清理**: `/tmp/hermes-verify-*` 驗證完成後必須 `rm -f` 清理。
- **編譯環境**: 子代理背景執行環境可能無 `.NET SDK`，委派編譯任務時需預先確認或改為靜態分析驗證。
- **SQL 注入修復模式**: 將 `string.Format("... WHERE x='{0}'", val)` 改為 `"WHERE x=@x" + GetDataTableParams(SQL, new SQLiteParameter("@x", val))` 或 Dapper 匿名物件風格。

# task_board.json 三階段生命周期（JL Lead）

本文件補充 `jl-delegation-workflow` 的工單狀態管理。對應 VPOS 的 TASK-009/010/015/016 教訓，改寫為 PHP/Layui 專案。

---

## 狀態機

```
TODO → IN_PROGRESS → REVIEW → (jl_qa 審查)
                          ├─ PASS → DONE
                          └─ REJECTED → IN_PROGRESS（開發者重修）→ REVIEW → ...
```

**禁止跳躍**：`REVIEW` 不得直接跳 `DONE`（會跳過開發者重修、失去 QA 閉環）。若發現此情形，立即補發修正任務給對應下屬。

---

## Phase 1：分析時（派單前）

Graphify 完成後、派單前讀取 `docs/task_board.json`：
- 任務不存在 → 建立物件（status=IN_PROGRESS 或 TODO）。
- 更新 `last_updated`。
- 用 `python3 -m json.tool docs/task_board.json` 驗證 JSON 語法正確。
- **Hermes_BK 備份**（見下方鐵律）。

### Step 1b：回答「還有哪些未完成」時的多檔案交叉核對（防呆）
當使用者問「目前狀態 / 還有哪些未完成項目」，**不得只信單一來源**——至少讀取三處並交叉比對：
1. `docs/task_board.json` —— **唯一權威來源**。用 `python3 -c "..."` 統計各 status 數量、列出所有非 DONE 的 Task。
2. `docs/gap-analysis.md`（或任何 checklist 型報告）—— 勾選框 `[ ]`/`[x]` **可能過時**，不代表實際完成。**必須以 task_board 為準**。若 gap-list 全 `[ ]` 但 task_board 多為 DONE → 該清單是舊版，應更新勾選或標註「此清單為 X 日舊版」。
3. `review-reports/issue-log.md` —— REJECTED 條目可能**已被主管親自重做並標 DONE**（task_board notes 會寫「實際由 jl_lead 親自執行…jl_ui 子代理卡死，已 stop」）。此為已解決、非阻塞。

**教訓（2026-09-17）**：gap-analysis.md 停在 2026-09-12，A1~E2 全 `[ ]`，但其中 A1/A2/A3/A4/B1~B6 其實已完成（T-19/T-20/T-21…）。若直接照 gap-list 回答「還剩 19 項未完成」會嚴重誤導。正確做法：task_board 為主 → 列出真正非 DONE 的 Task（本例只剩 T-23/L4-M4）→ 另註明「gap-analysis 勾選過時，建議更新」。

## Phase 2：子代理完成時

要求子代理標 `status=REVIEW`，並附上：
- `ls -la`（確認檔案已寫入）
- grep 驗證結果（如 PDO::prepare 數量、form.render 存在與否）

**派單提醒**：「完成後請將 task_board.json 中 Task 狀態更新為 REVIEW，並附上 ls -la 與 grep 實體寫入驗證結果。」

## Phase 3：QA PASS 後

jl_qa PASS → status=DONE + `qa_review="PASS"` + `qa_review_file`（報告路徑）+ `completed_date`。
更新 `last_updated` → python3 驗證 JSON → Hermes_BK 備份。

---

## ⚠️ JSON 更新注意事項（TASK-010a/b 教訓：sibling subagent 衝突）

**問題**：jl_qa 的 delegate_task 子代理嘗試更新 task_board.json，同時 jl_lead 也對同一檔案 patch。由於 sibling subagent 可能已改內容，patch fuzzy matching 會匹配到舊行號 → JSON 語法錯誤（JSONDecodeError）。

**對策**：
1. **先讀取** task_board.json → 確認當前狀態。
2. 若 sibling subagent 可能已修改 → 用 `write_file` **完整重寫**而非 `patch`。
3. **不要依賴 patch 的 fuzzy matching** 處理 JSON（JSON 對格式敏感）。
4. 更新後務必 `python3 -m json.tool docs/task_board.json` 驗證可解析。

---

## task_board.json 建議結構（JL Lead）

```json
{
  "project": "web-project",
  "version": "1.0.0",
  "last_updated": "2026-09-17T12:00:00+08:00",
  "tasks": [
    {
      "id": "TASK-001",
      "title": "人員資料管理 API",
      "type": "new_feature",
      "assignee": "jl_php",
      "status": "TODO",
      "files_affected": ["src/api/user.php"],
      "created_date": "2026-09-17",
      "completed_date": "",
      "graphify_query": "graphify query \"人員資料 CRUD\"",
      "description": "user.php 統一處理 list/create/update/delete，輸出 layui JSON",
      "qa_review": "",
      "qa_review_file": ""
    }
  ]
}
```

## 每輪開頭檢查

- [ ] task_board.json 是否有 REVIEW→DONE 跳過重修的情形？
- [ ] 每個 IN_PROGRESS/TASK 都有對應 Cron watchdog 嗎？
- [ ] JSON 語法是否仍正確（python3 -m json.tool）？

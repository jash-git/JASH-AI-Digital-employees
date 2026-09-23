---
name: subagent-delegation
description: Managing subagent delegation, cron monitoring, definition of done verification, and manual progress checks in CLI environments.
---

# Subagent Delegation & Monitoring

派單給子代理後，必須建立 Cron 監控排程與執行 Definition of Done 實體寫入驗證，這是鐵律。

## 核心流程

1. **派遣子代理** → `delegate_task()` 取得 `delegation_id`（大任務請先執行微步拆分 Micro-Tasks）
2. **立即建立 Cron 監控** → `cronjob(action='create', schedule='every 3m')`
   - **repeat 動態調整**: 
     - 簡單修復（≤5 處修改，如本次 TASK-015）→ `repeat=3`（約 9 分鐘內完成）
     - 中等任務（5~20 處修改）→ `repeat=6`（約 18 分鐘）
     - 大型重構（>20 處或跨檔案 cascade）→ `repeat=10`（約 30 分鐘）
   - 監控內容：檢查子代理狀態、檔案修改痕跡、是否卡死
   - 連續 3 次（約 9 分鐘）無進度 → 終止並重新派遣或改用 execute_code
3. **完成驗證與 QA 閉環** → 審查子代理提交之 `ls -la` 與 `grep` 結果，確認實體寫入後轉 QA[cite: 5, 7]

## 跨人格技能／記憶分發（2026-09-18 TASK-028 教訓）

當新增或更新 custom vpos skill / 各 persona MEMORY.md 時，必須按工作範圍同步到對應 profile。

### 關鍵事實：profile skills 是「複製」非 symlink
每個 profile（vpos_lead/core/ui/qa）的 `skills/` 目錄是**獨立副本**，不是連結。在一個 profile 新增 skill **不會**自動出現在其他 profile。必須手動 `cp -r` 分發，並用 `ls` 驗證。

### 分發矩陣（按下屬工作範圍）
| 技能／記憶類別 | lead | core | ui | qa |
|---|---|---|---|---|
| DB 層 audit skill（concurrency-audit、sqlite-connection-string-audit） | Y | **Y** | N（無 DB 範圍） | **Y** |
| 委派／QA 流程類（vpos-delegation-workflow、refactoring-qa-review、subagent-delegation） | Y | Y | **Y** | Y |
| MEMORY.md 教訓 | 寫入對應職責段落 | DB 根因+修復 | UI 重構教訓 | QA 審查重點 |

### 分發後驗證（必做）
```bash
for s in <skill names>; do printf "%-38s core=%s ui=%s qa=%s\n" "$s" \
  "$( [ -d profiles/vpos_core/skills/$s ] && echo Y || echo N )" \
  "$( [ -d profiles/vpos_ui/skills/$s ] && echo Y || echo N )" \
  "$( [ -d profiles/vpos_qa/skills/$s ] && echo Y || echo N )"; done
```
DB 層 skill → core+qa（ui 無 DB 範圍故不發）。分發後務必 `ls` 確認存在，再執行 Hermes_BK 備份。

## 手動檢查子代理進度的模式

當 Cron 回報無法自動送達時（CLI/TUI 環境限制），改用以下模式：

### 步驟 1：檢查檔案修改痕跡與時間戳記
```bash
ls -la <target_file>          # 比對修改時間是否為最新與檔案大小[cite: 5, 7]
git status <target_file>      # 確認是否有未提交修改
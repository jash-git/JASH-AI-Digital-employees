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

## 手動檢查子代理進度的模式

當 Cron 回報無法自動送達時（CLI/TUI 環境限制），改用以下模式：

### 步驟 1：檢查檔案修改痕跡與時間戳記
```bash
ls -la <target_file>          # 比對修改時間是否為最新與檔案大小[cite: 5, 7]
git status <target_file>      # 確認是否有未提交修改
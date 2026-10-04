---
name: crash-investigation
description: Agent/CLI 崩潰診斷 — CLI 突然退出或工作未完成時找出根因，並確認環境是否半完成
category: devops
---

# Crash Investigation（崩潰診斷）

## 觸發條件
- CLI 突然退出 / 使用者回報「你又崩了」「執行到一半跳出」
- delegate_task 子代理或 cron 工作沒有如期完成
- 某個 terminal 命令一直不回傳，之後對話中斷

## 核心原則
**「CLI 死了」≠「工作失敗」，也 ≠ 「環境壞了」。** 先區分哪一層出事，再確認副作用是否完整。崩潰常把任務停在半完成狀態（例如程式已部署但資料庫只建了一半），不可假裝沒事、也不可盲目重跑。

## 診斷流程（依序執行）

### 1. 區分「運行時死亡」與「工作失敗」
- CLI 退出只是互動式外殼死了；底層 gateway/後台工作可能完全健康。
- 先確認 gateway 是否仍在正常運作（檢查 gateway 進程 / gateway.log 最後時間戳），不要一崩就重啟整套環境。

### 2. 先排除資源耗盡（最快、最常見的真因之一）
- `dmesg | grep -iE "killed process|out of memory|oom"` → 有 OOM killer 記錄 = 記憶體爆掉。
- `free -h`（可用記憶體 / swap 使用）、`cat /proc/loadavg`、`ps --sort=-%mem`（誰在吃資源）。
- 若 dmesg 無 OOM、記憶體與 loadavg 正常 → 崩潰不是資源問題，進入下一步。

### 3. 找出「卡死點」= 崩潰起源
- 讀 agent.log / errors.log 最後成功回傳的 terminal 輸出——崩潰前最後一筆成功輸出就是停下的位置。
- 找連續的 `timed out after Ns`（例如三次各 420s）→ 某個命令一直不回傳被超時殺掉，這就是根因。
- 該卡死點之後的所有「應該完成」的副作用都視為未完成。

### 4. 掃荡殘留進程（重跑前必做）
- `ps aux | grep -iE "chrome|cdp|selenium|playwright|deploy|reset_db|seed" | grep -v grep`。
- 崩潰常留下懸空的 Chrome/CDP/deploy/sleep 進程，會干擾後續重跑或佔用資源。確認無殘留（或先 kill 掉）再繼續。

### 5. 逐階段獨立驗證副作用是否完整
- **不要**只憑「檔案存在」就宣告完成。把每個階段對照 source-of-truth 獨立檢查：
  - 程式碼：`md5sum src/... /deploy-path/...` 兩邊一致。
  - 資料庫：實際 `SHOW TABLES` / 查表是否存在，對照 `schema.sql`（崩潰常 DROP 完沒重建 → 部分表遺失）。
- 半完成狀態的經典模式：前端程式已部署、後端資料庫只建了一半。**每個階段都要單獨確認**，否則上線環境是坏的。

### 6. 回報根因 + 目前狀態，不假裝沒事
- 向使用者說明：崩在哪個步驟、為什麼（機制）、環境現在半完成到哪、下一步建議。
- 不要宣稱「已完成」直到每個階段都驗證通過。

## 支援檔案
- `references/hermes-crash-log-map.md` — Hermes 各日誌檔的位置與解讀方式（agent.log / errors.log / gateway-exit-diag.log / gateway.log）。
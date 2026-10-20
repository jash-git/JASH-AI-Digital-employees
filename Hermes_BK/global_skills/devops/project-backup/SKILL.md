---
name: project-backup
description: "Backup daytrade_scanner via sudo backup.sh; no manual tar."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [backup, devops, daytrade-scanner, hermes-bk]
    category: devops
---

# Project Backup（daytrade_scanner / Hermes 專案）

## When to Use
要備份 `/home/vblinux/daytrade_scanner`，或在 Hermes 專案下改了檔案後要做保護時。

## Correct Method — 用現成 script，不要手搓
> ⛔ **執行 `backup.sh` 前，若用戶指令沒「明說」要連 DB，先問（clarify）要不要備 state.db，不要直接預設不備就跑。**
> 觸發條件：用戶說「執行備份 / run backup / 備份一下」等模糊指令、卻沒提 `--state`/DB/memory → **必須先確認**。理由：含不含 DB 是有意義的決定（各 profile state.db 合計約 **590MB**），不是無傷大雅的預設值；直接跑掉會讓用戶以為「備好了」實際漏了記憶庫。
> - 用戶**明說**要連 DB（「連記憶一起備 / --state / include db」）→ 直接 `backup.sh --state`，不用問。
> - 用戶**明說**不要 DB → `backup.sh`（預設即可）。
> - 沒提 → 問：「這次要不要連各 profile 的 state.db（約 590MB、持久記憶庫）一起備？」再依回答執行。
```bash
sudo /home/vblinux/Hermes_BK/backup.sh          # 不含 DB（預設）
sudo /home/vblinux/Hermes_BK/backup.sh --state  # 含 state.db + -shm/-wal
```
- state.db 備份由 STATE_DB 控制：預設 0（不備）；`--state`=1、`--no-state`=0，env `BACKUP_STATE_DB` 可蓋過預設。
- 把 `/home/vblinux/daytrade_scanner` **整份拷貝**到 `Hermes_BK/Code/daytrade_scanner`（先 rm 舊的再重拷 = 自動更新）。
- 同時刷新所有 profile、global skills/memories、config_*.yaml、cron、SOUL.md，**以及每個 profile 的 state.db（含 `-shm`/`-wal` WAL sidecar）到 `Hermes_BK/state/<profile>/`**。state.db 才是各 profile 的持久記憶庫（非 memories/ 的 .md）。
- 驗證：跑完 `ls -la Hermes_BK/Code/daytrade_scanner/<你改的檔>` 時間戳有更新；state.db 則查 `Hermes_BK/state/<profile>/state.db` 大小是否與原檔一致。

## Pitfall（2026-10-13 實測教訓，必記）
⚠️ **不要為專案手搓 `tar czf` 快照**。`backup.sh` 已經把整個專案拷貝到 `Hermes_BK/Code/daytrade_scanner`，手搓 tar 是重複勞動（我曾多餘做了一个、後來刪掉）。要備接直接跑 backup.sh 就好。
- **state.db 用熱備份（hot copy）**：各 profile 的 state.db 是 SQLite WAL 模式，備份時連 `state.db-shm`、`state.db-wal` 一起拷貝以保持一致性；不必先 checkpoint（避免干擾正在跑的 gateway）。jl_lead/vpos_lead 單檔可達 200-360MB，整次備份需較長時間與空間。
- **profile 偵測只取目錄**：`profiles/` 下的 `config.yaml` 是檔案不是 profile，backup.sh 已用 glob `*/` 過濾，不會被當成假 profile 跑（2026-10-19 修）。
- 舊建議「改 universe.csv 前先 tar 至 `Hermes_BK/daytrade_scanner_bk/`」**已過時**，別遵循。
- **backup/restore 配對要「可選元件對稱」**：備份側加了任何 opt-in 可選開關（如 `--state` 控 state.db），還原側必須有對應處理，否則還原會**靜默丟掉已備份的資料**。實測 restore.sh 原本完全沒碰 `Hermes_BK/state/`——即使 backup.sh --state 備了 DB，跑 restore.sh 也不會還原。改任何一側的可選開關前，先 grep 另一側有無對應路徑；沒有就補對稱（restore.sh 已加 `--state` mirror backup.sh）。
- **`set -euo pipefail` 下 `[ cond ] && cmd` 在 cond 為 false 時會中斷腳本**：整行回傳非零被 `set -e` 當錯誤殺掉。要「條件式執行但不中斷」末尾加 `|| true`（backup.sh 建 state/ 目錄那行已修）。

## Restore（需要時）
- 專案：`Code/daytrade_scanner` 是普通目錄拷貝，還原就是 `cp -r Hermes_BK/Code/daytrade_scanner /target`。
- 全 Hermes 還原：`Hermes_BK/restore.sh`——**先讀懂再跑**（範圍大；會停/啟 `hermes-gateway.service`）。state.db 還原要 `--state`（與 backup.sh 對稱）：預設**不還原** DB，傳 `--state` 才把 `Hermes_BK/state/<profile>/` 的 state.db + `-shm`/`-wal` 一並寫回各 profile；沒傳或備份無 state/ 就跳過並印警告、不中斷。env `RESTORE_STATE_DB` 可蓋過預設。

## Notes
backup.sh 對 skills/memories/cron/config 是 clean-slate（rm -rf 後重 cp），會覆蓋現有備份。只有在你想「整批刷新」時才跑；只想補單檔不用動它。

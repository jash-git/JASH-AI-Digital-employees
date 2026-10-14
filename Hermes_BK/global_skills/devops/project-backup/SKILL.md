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
```bash
sudo /home/vblinux/Hermes_BK/backup.sh
```
- 自動 sudo（備份目錄 root 所有）；`set -euo pipefail`。
- 把 `/home/vblinux/daytrade_scanner` **整份拷貝**到 `Hermes_BK/Code/daytrade_scanner`（先 rm 舊的再重拷 = 自動更新）。
- 同時刷新所有 profile、global skills/memories、config_*.yaml、cron、SOUL.md。
- 驗證：跑完 `ls -la Hermes_BK/Code/daytrade_scanner/<你改的檔>` 時間戳有更新。

## Pitfall（2026-10-13 實測教訓，必記）
⚠️ **不要為專案手搓 `tar czf` 快照**。`backup.sh` 已經把整個專案拷貝到 `Hermes_BK/Code/daytrade_scanner`，手搓 tar 是重複勞動（我曾多餘做了一个、後來刪掉）。要備接直接跑 backup.sh 就好。
- 舊建議「改 universe.csv 前先 tar 至 `Hermes_BK/daytrade_scanner_bk/`」**已過時**，別遵循。

## Restore（需要時）
- 專案：`Code/daytrade_scanner` 是普通目錄拷貝，還原就是 `cp -r Hermes_BK/Code/daytrade_scanner /target`。
- 全 Hermes 還原：`Hermes_BK/restore.sh`——**先讀懂再跑**（範圍大）。

## Notes
backup.sh 對 skills/memories/cron/config 是 clean-slate（rm -rf 後重 cp），會覆蓋現有備份。只有在你想「整批刷新」時才跑；只想補單檔不用動它。

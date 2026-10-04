---
name: hermes-tool-lifecycle
category: devops
description: Register new tools in backup/restore + share skills across profiles.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [devops, tooling, backup, restore, workflow]
related_skills: [daytrade-next-day-open-scanner]
---

# Hermes 工具生命周期管理（新建工具 → 註冊備份/還原 → 同步技能）

## When to Use / 何時使用
每當在本環境**建立或修改任何工具**（腳本、專案、CLI）時都要執行。典型觸發：「我剛寫了個新工具/腳本」→ 要把它接進 backup.sh/restore.sh、建符號連結到 `~/.hermes/tools/`、把對應 skill 同步到所有 profile。這是強制流程，不是可選。

## 每個工具的三個位置
| 位置 | 路徑 | 用途 |
|---|---|---|
| **原始碼（實際執行）** | `/home/vblinux/<toolname>/` | 真正跑的地方 |
| **工具連結入口** | `~/.hermes/tools/<toolname>` → 原始碼 | 讓它被視為一個 tool |
| **備份副本** | `Hermes_BK/Code/<toolname>/` | backup.sh 自動管理 |

## 技能（skill）的存放與同步
- 位置：`/home/vblinux/.hermes/skills/<category>/<skill-name>/SKILL.md`
- backup.sh 的 `[1] Global skills` section 會整目錄拷貝 → `Hermes_BK/global_skills/`
- restore.sh 從 `global_skills/` 還原
- ⚠️ **全域技能不會自動同步到 profile**，必須手動拷貝（見末頁）

## 完整流程（五步，缺一不可）

### 1. 建立工具
```bash
mkdir -p /home/vblinux/<toolname>/ && cd /home/vblinux/<toolname>
# ...寫程式碼...
```

### 2. backup.sh 加 `[project]` section（放在 global skills 之後、global memories 之前）
```bash
echo "[project] Backing up /home/vblinux/<toolname>..."
if [ -d "/home/vblinux/<toolname" ]; then
    rm -rf "$BACKUP_ROOT/Code/<toolname>"
    mkdir -p "$BACKUP_ROOT/Code"
    cp -r "/home/vblinux/<toolname>" "$BACKUP_ROOT/Code/<toolname>"
    echo "  ✓ <toolname> backed up to $BACKUP_ROOT/Code/"
fi
```

### 3. restore.sh 加對應還原段（放在 per-profile loop 之後、`# --- Done` 之前）
```bash
echo "[project] Restoring /home/vblinux/<toolname>..."
PROJ_DST="/home/vblinux/<toolname>"
if [ -d "$BACKUP_ROOT/Code/<toolname>" ]; then
    copy="$(read_backup "$BACKUP_ROOT/Code/<toolname>")" || { echo "  ❌ Failed to read project backup"; }
    if [ -n "${copy:-}" ] && cp -a "$copy/." "$PROJ_DST/" 2>/dev/null; then
        chown -R "$(id -u):$(id -g)" "$PROJ_DST" 2>/dev/null || true   # backup 用 sudo → 檔是 root，還原改回 vblinux
        echo "  ✓ <toolname> restored -> $PROJ_DST"
    fi
    [ -n "${copy:-}" ] && rm -rf "$(dirname "$copy")" 2>/dev/null || true
else
    echo "  ⚠ No <toolname> in backup (Hermes_BK/Code/<toolname>)"
fi
echo "[tool] Rebuilding ~/.hermes/tools/<toolname> symlink..."
ln -sfn "$PROJ_DST" "$HERMES_DIR/tools/<toolname>" && echo "  ✓ symlink -> $HERMES_DIR/tools/<toolname>"
```

### 4. 建立符號連結
```bash
ln -sfn /home/vblinux/<toolname> ~/.hermes/tools/<toolname>
```

### 5. 跑備份 + 驗證
```bash
cd /home/vblinux/Hermes_BK && sudo bash backup.sh   # 需 sudo（免密碼）
diff <(cat /home/vblinux/.hermes/skills/<cat>/<skill>/SKILL.md) \
     <(cat /home/vblinux/Hermes_BK/global_skills/<cat>/<skill>/SKILL.md) && echo "✅ skill 已同步"
ls -la /home/vblinux/Hermes_BK/Code/<toolname>/    # 確認專案已備份
```

## 已知坑（本環境實測）
1. **ownership**：backup.sh 用 sudo → 拷貝檔是 root 所有；restore.sh 必須 chown 回 vblinux，否則 Hermes 權限壞掉。
2. **非增量**：backup.sh 用 `rm -rf` + `cp -r`（整目錄重建），沒有版本歷史。要留舊版得另外做 git 或時間戳。
3. **符號連結不備份**：backup.sh 不碰 `~/.hermes/tools/`，但 restore.sh 會重建連結。還原後連結一定在。
4. **facts.json 勿手改**：`~/.hermes/tools/facts.json` 是安裝器管理的 manifest（含 artifact digest），手動連結的工具不要寫進去。
5. **跑前語法檢查**：改 backup.sh/restore.sh 後先 `bash -n script.sh`，確認無誤再執行。

## 把技能同步到所有 profile
全域技能不自動同步。8 個 profile（jl_lead/jl_php/jl_qa/jl_ui/vpos_core/vpos_lead/vpos_qa/vpos_ui）各自獨立 skills/：
```bash
for p in jl_lead jl_php jl_qa jl_ui vpos_core vpos_lead vpos_qa vpos_ui; do
    cp -r /home/vblinux/.hermes/skills/<cat>/<skill> \
          /home/vblinux/.hermes/profiles/$p/skills/ 2>/dev/null && echo "✓ $p"
done
```
（default profile = /home/vblinux/.hermes，已在全域技能範圍內，不需拷貝）

## 具體範例：daytrade_scanner
- 原始碼：`/home/vblinux/daytrade_scanner/`（scanner.py、backtest_v2.py、scan_on_date*.py、results/*.md）
- 連結：`~/.hermes/tools/daytrade_scanner`
- 備份：`Hermes_BK/Code/daytrade_scanner/`
- 技能：`finance/daytrade-next-day-open-scanner`（怎麼用選股工具，見該技能）

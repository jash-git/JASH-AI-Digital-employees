# Hermes_BK 備份腳本運作原理說明

## 一、總覽

`backup.sh` 是一個 Bash 腳本，用途是把 **Hermes Agent 的所有設定資料**（全域 + 各 profile）整份複製到 `/home/vblinux/Hermes_BK/` 這個「備份根目錄」。

它只備份「有意義的設定檔」，不會碰 runtime 產生的大檔案（state.db、cache、logs、sessions…）。

## 二、前置條件與執行方式

- **必須有 sudo**：因為備份目的地 `Hermes_BK/*` 是 root 所有（owner=root），一般使用者無法寫入。
- 腳本內建「自動升權」：若以非 root 執行，會 `exec sudo "$0"` 重新用 root 跑一次（第 9-12 行）。
- 開頭 `set -euo pipefail`：任何指令失敗就立即終止，避免半套備份。

## 三、目錄對應關係（來源 → 目的地）

| 來源（Hermes 實際位置） | 備份存放位置（Hermes_BK/） |
|---|---|
| `~/.hermes/skills/*` | `global_skills/` |
| `~/.hermes/memories/*` | `global_memories/` |
| `~/.hermes/SOUL.md` | `人格檔/global_SOUL.md` |
| `~/.hermes/config.yaml` | `config.yaml` |
| `~/.hermes/profiles/<p>/skills/*` | `skills/<p>/` |
| `~/.hermes/profiles/<p>/memories/*` | `memories/<p>/` |
| `~/.hermes/profiles/<p>/SOUL.md` | `人格檔/<p>_SOUL.md` |
| `~/.hermes/profiles/<p>/config.yaml` | `config_<p>.yaml` |
| `~/.hermes/profiles/<p>/cron/*` | `cron/<p>/` |

> `<p>` 是 profile 名稱。腳本會自動偵測 profiles 目錄下的所有資料夾，無需改碼即可支援新增 profile。

## 四、執行流程（依序）

1. **自動升權**：非 root → 用 sudo 重跑。
2. **抓時間戳與路徑**：`TIMESTAMP=$(date +%Y%m%d_%H%M%S)`，定義各來源/目的地變數。
3. **自動偵測 profiles**：`ls -1 profiles/` 列出所有 profile 名稱（空白則 fallback 到 `jl_lead`）。
4. **🧹 清空舊備份**（第 46-48 行，關鍵步驟）：
   - `rm -rf` 掉 `skills/ memories/ cron/ 人格檔/ global_skills/ global_memories/` 全部資料夾。
   - `rm -f` 掉所有 `config_*.yaml` 與 `config.yaml`。
   - 重新建立這些空資料夾。
   - **原因**：`cp -r` 到已存在的資料夾會「合併/覆蓋」，行為不可預測；先清空才能確保每次都是乾淨的全新備份（避免殘留舊資料）。
5. **依序複製**：
   - [1] 全域 skills → `global_skills/`
   - [2] 全域 memories → `global_memories/`
   - 逐 profile 迴圈：skills → `skills/<p>/`、memories → `memories/<p>/`、SOUL.md → `人格檔/<p>_SOUL.md`、config.yaml → `config_<p>.yaml`、cron → `cron/<p>/`
   - [soul] 全域 SOUL.md → `人格檔/global_SOUL.md`
   - [config] 全域 config.yaml → `config.yaml`
6. **結尾報告**：列出備份根目錄內容與各資料夾大小（`du -sh`）。

## 五、重要特性與限制

- **隔離式記憶**：每個 profile 的 memories/skills 各自獨立存放，互不混。
- **非增量**：每次都是全量重建（先刪後存），不會保留歷史版本。
- **不含 runtime 資料**：state.db、cache、logs、sessions、vault、workspace 等都不備份。
- **目的地 root 所有**：備份出來的檔案 owner=root，但權限是 755（world-readable），一般使用者可讀不可寫。
- **config.yaml 命名規則**：`config_<profile>.yaml`；全域就是 `config.yaml`。

## 六、還原對應原則與 gateway 管理

還原腳本 `restore.sh` 把上面的映射「反過來」，並自動管理 gateway（user systemd service `hermes-gateway.service`）：

- **需要 sudo（但只讀不寫）**：備份檔案實際是 mode 600、root 所有，一般使用者連讀都讀不到。所以還原用 `sudo cat` 讀取、再寫回 vblinux 擁有的目的地，保持 `~/.hermes` 仍是 user 所有。腳本絕不會讓 sudo 直接寫入 `~/.hermes`（否則會把檔案寫成 root 所有、破壞權限）。
- **還原前自動停 gateway**：避免寫入時被佔用或覆蓋進行中的變更。
- **還原後重啟 gateway**：停在「review」階段等你確認，輸入 `skip` 可保持關閉（手動 `systemctl --user start hermes-gateway.service`）。
- **`--no-gateway` 參數**：跳過所有 gateway 操作（適合無法管理服務的環境）。

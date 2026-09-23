# Apache 路由問題 — 2026-08-01 部署實錄

## 問題描述

專案原始碼只包含 `router.php`，但 Apache 不會自動執行它。Apache 的 `DirectoryIndex` 預設只找 `index.html` / `index.php`，所以：
- 訪問 `/` → 顯示 404 或目錄列表
- `.htaccess` 中的 RewriteRule 無效（因為 `mod_rewrite` 未啟用 + `AllowOverride None`）

## 被迫的臨時修復

1. 建立 `index.php`（從 `router.php` 複製內容）
2. 建立 `.htaccess`（RewriteRule 指向 index.php）
3. `sudo a2enmod rewrite`
4. 建立 VirtualHost 設定 `AllowOverride All`
5. `systemctl restart apache2`

## 正確的預防做法

**所有專案的 `src/` 根目錄必須包含以下檔案：**

| 檔案 | 用途 |
|:---|:---|
| `.htaccess` | Apache RewriteRule + DirectoryIndex |
| `index.php` | 路由核心（靜態檔案 vs API 路由） |

**不得**假設伺服器已配置 rewrite 模組或 AllowOverride。

## 相關技能

- `deployment-checklist` — 完整部署檢查清單
- `lamp-stack-installation` — LAMP 環境安裝

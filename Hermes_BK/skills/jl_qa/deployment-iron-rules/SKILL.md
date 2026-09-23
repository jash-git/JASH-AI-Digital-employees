---
name: deployment-iron-rules
description: 部署鐵律 — 伺服器設定優先，嚴禁以修改程式碼補丁部署缺失
category: devops
---

# Deployment Iron Rules

## 核心原則
**部署時專注於伺服器設定與檔案佈署，嚴禁大量修改程式碼作為變通手段。**

## 部署前檢查清單
1. Apache 模組是否已啟用：`a2enmod rewrite`、`a2enmod headers`
2. AllowOverride 是否設定為 `All`（讓 .htaccess 生效）
3. .htaccess 是否存在且語法正確
4. index.php 是否作為入口檔案存在

## 遇到程式碼需要修改才能跑時
**停下來，先檢查部署設定：**
- 問題 1：Apache mod_rewrite 沒啟用 → `a2enmod rewrite && systemctl restart apache2`
- 問題 2：AllowOverride None → 改 Apache vhost 設定為 AllowOverride All
- 問題 3：.htaccess 遺失或語法錯誤 → 補上正確的 .htaccess
- 問題 4：index.php 路由檔案不存在 → 補上入口檔案

## 程式碼修改的紅線
- ✅ 允許：修復真正存在的程式錯誤（邏輯錯誤、Bug）
- 🚫 禁止：為補丁部署設定缺失而改程式碼
- 🚫 禁止：用 index.php 硬編碼路由取代 .htaccess 的意義
- 🚫 禁止：修改 API 路徑或控制器來配合錯誤的伺服器設定

## 部署流程（四階段）
1. **資料庫基建**：建表 + 預設資料
2. **覆蓋佈署**：清空測試環境 → 複製 src/ 內容
3. **權限配置**：chown www-data:www-data，dir=755，file=644
4. **瀏覽器測試**：實際訪問測試環境網址驗證

## Docker Mount 權限陷阱（重要）

當 `/var/www/html` 是 Docker mount point 時，常規的 `rm -rf /var/www/html/*` + `cp -r src/ /var/www/html/` 會失敗（PermissionError），因為 mount 介面的檔案由容器擁有者控制。

**正確做法**：
1. **先檢查是否為 Docker mount**：`df -h /var/www/html` 或 `mount | grep www`
2. **使用 `sudo cp` 覆蓋**（而非 `rm + cp`）：
   ```bash
   sudo cp src/public/index.html /var/www/html/
   sudo mkdir -p /var/www/html/api /var/www/html/config
   sudo cp src/api/bazireport.php /var/www/html/api/
   sudo cp src/config/.env /var/www/html/config/
   ```
3. **權限設定**：`sudo chown -R www-data:www-data /var/www/html/api /var/www/html/config`

**檢查清單**：部署前執行 `stat -c '%a %U:%G' /var/www/html/index.html`，若 Owner 是 `root` 而非 `www-data`，表示是 Docker mount，需用 `sudo cp`。

## 部署後
- 執行 `graphify .` 更新知識圖譜
- 確認所有工單狀態為 DONE
- 向使用者匯報佈署結果
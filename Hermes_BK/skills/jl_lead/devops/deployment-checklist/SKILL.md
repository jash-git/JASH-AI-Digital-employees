---
name: deployment-checklist
description: 部署前檢查清單 - 確保 Apache/Nginx 配置、路由、權限正確，避免部署時臨時修改程式碼
category: devops
---

# 部署前檢查清單 (Deployment Checklist)

## 觸發條件
當任何任務涉及「佈署到測試環境」或「伺服器配置」時，必須先檢查以下項目。

## 檢查項目

### 1. 伺服器配置檔案 (必須存在於 src/ 中)
- [ ] `.htaccess` (Apache) 或 `nginx.conf` (Nginx) 必須包含在原始碼中
- [ ] 路由檔案必須命名為 `index.php` 或 `.htaccess` 中必須有正確 RewriteRule
- [ ] 如果專案使用 `router.php` 作為路由，**必須同時提供 `.htaccess` 設定**：
  ```apache
  RewriteEngine On
  DirectoryIndex index.php
  RewriteCond %{REQUEST_FILENAME} -f [OR]
  RewriteCond %{REQUEST_FILENAME} -d
  RewriteRule ^ - [L]
  RewriteRule ^(.*)$ index.php [L]
  ```

### 2. 檔案權限預設值
- [ ] 所有 PHP 檔案預設應為 `644` (rw-r--r--)
- [ ] 所有目錄預設應為 `755` (rwxr-xr-x)
- [ ] `.env` 檔案應為 `600` (rw-------) 或 `640`
- [ ] **禁止**在程式碼中硬編碼權限設定

### 3. Apache 模組檢查
- [ ] `mod_rewrite` 必須啟用 (`a2enmod rewrite`)
- [ ] `mod_php` 必須啟用
- [ ] `AllowOverride All` 必須設定在 DocumentRoot
- [ ] 佈署後必須執行 `systemctl restart apache2`

### 4. 資料庫檢查
- [ ] 資料庫名稱與 `.env` 中一致
- [ ] `schema.sql` 必須包含 `CREATE TABLE IF NOT EXISTS`
- [ ] 預設帳號/密碼必須存在於 `schema.sql` 中
- [ ] 密碼必須使用 `password_hash()` 生成

### 5. 路由與靜態檔案
- [ ] 靜態檔案路徑必須正確對映到 `public/` 目錄
- [ ] API 路由必須以 `/api/` 開頭
- [ ] 根路徑 `/` 必須導向登入頁面或儀表板

## 常見錯誤 (Pitfalls)

### 錯誤 1: Apache 不執行 router.php
**症狀**: 訪問網站顯示 404 或目錄列表
**原因**: Apache 預設不執行非 `index.php` 的 PHP 檔案
**解法**: 
- 將路由檔案命名為 `index.php`，或
- 在 `.htaccess` 中設定 `DirectoryIndex index.php` 並加入 RewriteRule

### 錯誤 2: 檔案權限 600 導致 PHP 無法讀取
**症狀**: PHP 出現 "Permission denied" 錯誤
**原因**: 檔案複製後權限變成 600，Apache 使用者 (www-data) 無法讀取
**解法**: 佈署後執行 `chmod -R 644 /var/www/html/`

### 錯誤 3: mod_rewrite 未啟用
**症狀**: `.htaccess` 中的 RewriteRule 無效
**原因**: Apache 預設未啟用 rewrite 模組
**解法**: 執行 `a2enmod rewrite && systemctl restart apache2`

### 錯誤 4: AllowOverride 未設定
**症狀**: `.htaccess` 設定被忽略
**原因**: Apache 預設 `AllowOverride None`
**解法**: 在 VirtualHost 中設定 `AllowOverride All`

### 錯誤 5: `mime_content_type()` 回傳 text/plain 導致 CSS 無效
**症狀**: 頁面完全沒有排版，瀏覽器 Network 面板顯示 CSS 的 Content-Type 為 `text/plain` 而非 `text/css`
**原因**: PHP 的 `mime_content_type()` 依賴 fileinfo 資料庫，當檔案內容被壓縮成單行（如 minified CSS/JS），資料庫無法正確識別 MIME Type
**解法**: **不要使用 `mime_content_type()`**。改用副檔名映射表（`.css` → `text/css`, `.js` → `application/javascript` 等）。詳細參考 `references/php-router-mime-type-pitfall.md`

### 錯誤 6: 根路徑 `/` 顯示 Apache 目錄列表
**症狀**: 訪問 `http://localhost/` 看到「Index of /」目錄列表，而非登入頁面
**原因**: 
1. 部署根目錄沒有 `index.html` 或 `index.php` 作為預設文件
2. `.htaccess` 的 RewriteRule 把根路徑請求導向 `index.php`，但 `index.php` 可能不在正確位置或 PHP 執行有問題
3. `.htaccess` 的 RewriteRule 沒有排除 `/public/` 靜態檔案路徑，導致 `http://localhost/public/login.html` 也被導向 `index.php`
**解法**:
- **部署根目錄必須提供 `index.html`**（HTML 重導向即可），內容如：
  ```html
  <!DOCTYPE html>
  <html><head><meta http-equiv="refresh" content="0;url=/public/login.html"></head>
  <body><script>window.location.href='/public/login.html';</script></body></html>
  ```
- **`.htaccess` 必須排除 `/public/` 和 `/api/` 路徑**，在 RewriteRule 之前加上：
  ```apache
  RewriteCond %{REQUEST_URI} ^/public/
  RewriteRule ^public/(.*)$ public/$1 [L]
  RewriteCond %{REQUEST_URI} ^/api/
  RewriteRule ^api/(.*)$ api/$1 [L]
  ```
- 參考 `references/apache-root-path-deploy.md`

### 錯誤 7: 修正後使用者回報「還是一樣」— 瀏覽器快取
**症狀**: 你已經修改了 HTML/CSS 並重新佈署，但使用者截圖看起來跟之前一樣
**原因**: 瀏覽器快取了舊版 CSS 或 JS 檔案（`.css`、`.js` 特別容易被快取）
**解法**:
1. 先確認伺服器端檔案已更新：`grep -A 3 "login-footer" /var/www/html/public/css/style.css`
2. 通知使用者 **Ctrl+Shift+R**（強制重新整理）或開啟**無痕模式**測試
3. 如果問題持續，再懷疑程式碼本身
**預防**: 在靜態檔案連結加上版本參數，如 `<link href="css/style.css?v=2">`

### 錯誤 8: 部署後未用瀏覽器實際驗證
**症狀**: 用 terminal 確認檔案已複製，就以為部署成功
**原因**: terminal 複製 ≠ 瀏覽器能正常渲染
**解法**: **每次佈署後必須用瀏覽器實際訪問**：
1. `browser_navigate` 到測試環境網址
2. `browser_vision` 截圖確認畫面正確
3. `browser_console` 檢查 JavaScript 錯誤
4. 測試關鍵功能（登入、API 呼叫）
5. 確認無誤後才算部署完成

### 錯誤 9: 下屬只改 src/ 卻漏掉實際佈署，且報告聲稱已完成
**症狀**: delegate_task 子代理回傳「completed_verified」，但 `docs/task_board.json` 標 DONE 後上線環境仍是舊版（md5 不符、grep 找不到新程式碼）
**原因**: 
1. 子代理在 `src/` 工作目錄改好檔案，卻忘記執行 `sudo cp` / rsync 到測試環境（如 `/var/www/html/`）
2. 子代理的自我檢查只驗證「檔案是否存在」，無法發現「部署步驟被跳過」
3. 子代理報告不可信——它可能真的以為自己佈署了，或結尾 JSON 寫入錯誤掩蓋了實際失敗
**解法（主管/控制器必須親自核實，絕不信任子代理報告）**:
1. **md5 比對**：`md5sum src/public/js/X.js /var/www/html/js/X.js`——兩邊必須完全一致。不一致 = 未部署或部署不完整。
2. **grep 查證**：在部署路徑直接 `grep -c "新程式碼特徵字串" /var/www/html/...`，確認新邏輯真的上線（不是只改 src）。
3. **API curl**：若是後端功能，POST/curl 實際呼叫測試環境 API，確認回傳正確 JSON。
4. **只有 md5 一致 + grep 找到 + （必要時）curl 通過**，才算該微步真正完成；否則退回重派子代理或親自部署。
**預防**: 在委派給 jl_ui / jl_php 的 prompt 中明確要求「完成後必須執行 `sudo cp src/... /var/www/html/...` 並回報 md5」；控制器收到報告後仍須獨立核實。

### 錯誤 10: 從子目錄頁面點擊導覽連結全崩（相對連結陷阱）
**症狀**: 使用者回報「在首頁點正常，但進到某個子頁面後，其他導覽連結全部 404」；直接 curl 那些目標檔永遠回 200。
**原因**: nav/footer 用**相對連結**（如 `href="cate/geju.html"`）。從根目錄解析正確（→ `/cate/geju.html`），但當使用者已經在子目錄頁面（如 `/type/dianji.html`）時，同一個相對連結會被瀏覽器解析成 `/type/cate/geju.html` → 404。
**解法**: **把所有導覽連結改成絕對路徑**（加 `/` 前綴：`href="/cate/geju.html"`）。巡檢時要把每個相對連結「相對於該檔案所在目錄」解析後再 curl，不是相對於根目錄。完整方法與腳本見 `references/link-integrity-audit.md`。

### 錯誤 11: 頁面能載入但渲染空白（空殼）
**症狀**: curl 回 200、HTML 結構完整（有表單/按鈕），但瀏覽器實際畫面是空白或內容沒顯示。
**原因**: **執行時 JS 報錯**（API 404、ReferenceError、`form.render()` 失敗等），非 HTTP 層級問題。curl 完全看不出來。
**解法**: 用瀏覽器實際載入並截圖 + 讀 `document.body.innerText.length` + 監聽 console error（error/404/undefined/ReferenceError）定位，不是再 curl。完整方法見 `references/link-integrity-audit.md`「空殼頁面偵測」。

## 佈署命令模板

```bash
# 1. 清空測試環境
sudo rm -rf /var/www/html/*

# 2. 複製檔案
sudo cp -r src/* /var/www/html/

# 3. 設定權限
sudo chown -R www-data:www-data /var/www/html/
sudo find /var/www/html/ -type d -exec chmod 755 {} \;
sudo find /var/www/html/ -type f -exec chmod 644 {} \;

# 4. 啟用 Apache 模組
sudo a2enmod rewrite
sudo systemctl restart apache2

# 5. 資料庫初始化 (如果尚未建立)
sudo mysql -u root -e "CREATE DATABASE IF NOT EXISTS $(grep DB_NAME src/config/.env | cut -d= -f2) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -u root $(grep DB_NAME src/config/.env | cut -d= -f2) < src/config/schema.sql
```

## 瀏覽器自動化測試清單

佈署完成後，必須執行以下瀏覽器測試：

1. **登入頁面載入**: `http://localhost/` → 顯示 login.html
2. **表單驗證**: 空白欄位無法送出
3. **正確帳密登入**: admin/admin123 → 跳轉至 index.html
4. **錯誤帳密登入**: API 回傳 `{"code":1001,"msg":"帳密錯誤"}`
5. **儀表板顯示**: 側邊欄、統計卡片正常渲染
6. **登出確認**: 彈出確認對話框
7. **登出跳轉**: 跳回 login.html
8. **API 測試**: `check.php` 回傳正確 JSON

## 支援檔案

- `references/apache-routing-pitfall.md` — Apache 路由問題實錄（2026-08-01），router.php 不生效的完整案例分析與預防做法
- `scripts/backup.sh` — 全 Profile 備份腳本（skills/memories/SOUL.md/config.yaml）

## 部署完成後必做 (Post-Deployment)

**以下步驟在「所有工單 DONE + 瀏覽器測試通過」後執行，缺一不可：**

1. **執行 `graphify .` 生成知識圖譜**
   ```bash
   cd /path/to/project
   graphify . --code-only          # 無 LLM API key 時用此模式
   graphify cluster-only .         # 產生 GRAPH_REPORT.md
   ```
   **⚠️ 2026-08-01 教訓：** 部署完成後忘記執行 graphify，導致圖譜未更新。此步驟為部署流程的最後一步。

2. **執行全 Profile 備份**
   ```bash
   bash /home/vblinux/Hermes_BK/backup.sh
   ```

3. **更新 `docs/task_board.json` 狀態為 DONE**

4. **向使用者總結匯報**

## 鐵律：嚴禁以程式碼補丁部署設定缺失 (2026-08-03)

> **此鐵律優先於所有其他流程。**

### 觸發條件
- 部署時發現程式碼無法正常運作
- 需要修改程式碼才能讓系統跑起來

### 處置程序
1. **立即停止修改程式碼**
2. **回頭檢查伺服器設定**：
   - Apache 模組是否啟用 (`mod_rewrite`)
   - `AllowOverride All` 是否設定
   - `.htaccess` 是否正確
   - VirtualHost 設定是否完整
3. **修正伺服器設定後重新佈署**

### 禁令
- 🚫 **嚴禁修改程式碼來補丁伺服器設定缺失**
- 🚫 **嚴禁在程式碼中加入 Apache/Nginx 配置的 workaround**
- 🚫 **嚴禁以程式碼修改作為部署流程的變通手段**

### 例外
- 程式碼本身有真正的錯誤（語法錯誤、邏輯錯誤）
- 需要新增 `.htaccess` 或 `index.php` 作為標準部署檔案（這不算補丁，這是標準流程）

### 下屬約束 (jl_php, jl_ui)

- **jl_php**: 必須在 `src/` 中包含 `.htaccess` 或 `nginx.conf`，不得假設伺服器已配置
- **jl_php**: 路由檔案必須命名為 `index.php` 或提供完整路由設定
- **jl_ui**: 靜態檔案路徑必須與 `.htaccess` 設定一致
- **雙方**: 不得在程式碼中硬編碼伺服器配置
- **雙方**: 開發時假設伺服器已正確配置，不得寫 workaround
---
name: deployment-checklist
description: 部署前檢查清單 - 確保 Apache/Nginx 配置、路由、權限正確，避免部署時臨時修改程式碼
---

# 部署檢查清單 (Deployment Checklist)

## 觸發條件
- 收到「佈署」或「部署」指令時
- 所有工單狀態均為 `DONE` 時

## 部署前檢查

### 1. 伺服器設定檢查（優先於程式碼修改）
- [ ] **Apache mod_rewrite 已啟用**：`sudo a2enmod rewrite`
- [ ] **AllowOverride All 已設定**：Apache VirtualHost 或 .htaccess 允許覆寫
- [ ] **.htaccess 路由檔案存在**：必須包含正確的 RewriteRule
- [ ] **index.php 入口檔案存在**：作為所有請求的統一入口

### 2. 程式碼檢查（僅限真正錯誤）
- [ ] **嚴禁以程式碼補丁修復伺服器設定缺失**
- [ ] **嚴禁硬編碼帳號密碼**：一律使用 `.env`
- [ ] **PHP 使用 declare(strict_types=1)**
- [ ] **所有 DB 操作使用 PDO 預處理**
- [ ] **前端使用本地資源，無 CDN 依賴**

### 3. 部署步驟

#### 第一階段：資料庫基建
```bash
mysql -u webapp -p'webapp_password_123' webapp_db < src/config/schema.sql
```
- 確認所有資料表欄位已建立
- 確認預設/內建資料已初始化

#### 第二階段：清空並覆蓋佈署
```bash
sudo rm -rf /var/www/html/*
sudo cp -r src/public src/api src/config src/.htaccess src/index.php /var/www/html/
```
- **清空既有內容**
- **直接佈署 src/ 內容到測試環境根目錄**
- **嚴禁建立虛擬目錄或多餘層級**

#### 第三階段：權限配置
```bash
cd /var/www/html
sudo chown -R www-data:www-data .
sudo find . -type d -exec chmod 755 {} \;
sudo find . -type f -exec chmod 644 {} \;
```

#### 第四階段：瀏覽器自動化測試
- 啟動瀏覽器測試 http://localhost/
- 測試登入 → 功能操作 → 無 JavaScript 錯誤
- **測試失敗則視為佈署未完成，回頭檢查伺服器設定**

#### 第五階段：圖譜同步
```bash
cd /home/vblinux/test-project
graphify . --code-only  # 若無 LLM API key
graphify cluster-only   # 產生 GRAPH_REPORT.md
```

## 常見錯誤與處置

### ❌ 錯誤：Apache 無法執行 router.php
**原因**：Apache 不會自動執行非 index.php 的檔案
**處置**：
1. 建立 `.htaccess` 設定 RewriteRule
2. 建立 `index.php` 作為統一入口
3. **不要修改 router.php 來補丁這個問題**

### ❌ 錯誤：403 Forbidden
**原因**：目錄權限或 AllowOverride 設定問題
**處置**：
1. 檢查 Apache VirtualHost 設定 `AllowOverride All`
2. 確認 `.htaccess` 檔案存在且權限正確
3. **不要修改程式碼權限來補丁伺服器設定**

### ❌ 錯誤：500 Internal Server Error
**原因**：PHP 語法錯誤或 PHP 版本不相容
**處置**：
1. 檢查 PHP 錯誤日誌：`sudo tail -f /var/log/apache2/error.log`
2. 確認 PHP 版本 ≥ 8.0
3. 檢查 `declare(strict_types=1)` 語法

## 鐵律
> **部署時應專注於伺服器設定與檔案佈署，嚴禁大量修改程式碼作為變通手段。**
> **若發現需要改程式碼才能跑，代表部署流程或伺服器設定有問題，應回頭檢查：**
> 1. Apache 模組是否啟用 (mod_rewrite)
> 2. AllowOverride 是否設定
> 3. .htaccess 是否正確
> **程式碼修改只限於修復真正錯誤，不應用於補丁部署設定缺失。**

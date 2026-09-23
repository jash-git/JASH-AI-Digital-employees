# Apache 根路徑部署 — 2026-08-03

## 問題描述
專案部署到 Apache 後，訪問 `http://localhost/` 顯示「Index of /」目錄列表，而非登入頁面。

## 原因分析
1. 部署根目錄 `/var/www/html/` 沒有 `index.html` 或 `index.php` 作為 DirectoryIndex
2. `.htaccess` 的 RewriteRule 把所有請求導向 `index.php`，但 `index.php` 可能位置錯誤或 PHP 執行有問題
3. `.htaccess` 沒有排除 `/public/` 和 `/api/` 路徑，導致靜態檔案也被導向 `index.php`

## 正確部署結構
```
/var/www/html/
├── .htaccess          # 路由規則（排除 public/ 和 api/）
├── index.html         # 根目錄重導向 → /public/login.html
├── public/
│   ├── index.html     # 首頁（登入後）
│   ├── login.html     # 登入頁
│   ├── css/
│   │   └── style.css
│   └── lib/
│       └── layui/
├── api/
│   └── auth/
│       └── login.php
└── config/
    └── .env
```

## .htaccess 正確寫法
```apache
RewriteEngine On

# 排除 public/ 靜態檔案
RewriteCond %{REQUEST_URI} ^/public/
RewriteRule ^public/(.*)$ public/$1 [L]

# 排除 api/ API 路由
RewriteCond %{REQUEST_URI} ^/api/
RewriteRule ^api/(.*)$ api/$1 [L]

# 其他請求導向 index.php（如果需要 PHP 路由）
# 如果不需要，可以刪除這段
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ index.php [QSA,L]
```

## index.html 重導向
```html
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0;url=/public/login.html">
    <title>重導中...</title>
</head>
<body>
    <p>正在跳轉到登入頁面...</p>
    <script>window.location.href='/public/login.html';</script>
</body>
</html>
```

## 部署命令
```bash
cd /home/vblinux/test-project
DEPLOY_PATH=$(grep DEPLOY_TEST_PATH src/config/.env | cut -d= -f2)

# 清空並複製
sudo rm -rf "${DEPLOY_PATH:?}"/*
sudo cp -r src/* "$DEPLOY_PATH"/

# 權限設定
sudo chown -R www-data:www-data "$DEPLOY_PATH"
sudo find "$DEPLOY_PATH" -type d -exec chmod 755 {} \;
sudo find "$DEPLOY_PATH" -type f -exec chmod 644 {} \;
```

## 瀏覽器驗證
佈署後必須用瀏覽器測試：
1. 打開 `http://localhost/` → 應自動導向 `/public/login.html`
2. `browser_vision` 截圖確認畫面
3. `browser_console` 檢查無 JavaScript 錯誤
4. 測試登入功能

## 常見陷阱
- **瀏覽器快取**: 修改 CSS/JS 後使用者看到舊畫面，請要求 Ctrl+Shift+R
- **PHP 執行問題**: 如果 .htaccess 導向 index.php 但 PHP 執行有問題，改用 HTML 重導向
- **權限問題**: 複製後檔案權限可能變成 600，PHP 無法讀取

# PHP 路由 MIME Type 陷阱 — 2026-08-03 實錄

## 問題描述

路由使用 `mime_content_type()` 自動偵測靜態檔案的 MIME Type，但當檔案內容被壓縮成單行（如 minified CSS/JS），PHP 的 fileinfo 資料庫會**無法正確識別**，回傳 `text/plain`。

瀏覽器收到 `text/plain` 的 CSS 檔案時，不會當樣式表渲染，導致頁面**完全沒有排版**。

### 診斷方法

```bash
# 檢查 Apache 回傳的 Content-Type
curl -sI http://localhost/lib/layui/css/layui.css | grep Content-Type
# 錯誤結果: Content-Type: text/plain;charset=UTF-8
# 正確結果: Content-Type: text/css;charset=UTF-8

# 檢查 PHP CLI 是否能正確識別
php -r "echo mime_content_type('/path/to/file.css');"
# 可能回傳: text/plain（即使 fileinfo 模組已安裝）
```

## 解法

**不要使用 `mime_content_type()`**，改用副檔名映射表：

```php
$mimeTypes = [
    '.css'  => 'text/css',
    '.js'   => 'application/javascript',
    '.html' => 'text/html',
    '.json' => 'application/json',
    '.png'  => 'image/png',
    '.jpg'  => 'image/jpeg',
    '.woff2'=> 'font/woff2',
    // ... 等
];
$ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
$mimeType = $mimeTypes['.' . $ext] ?? 'application/octet-stream';
```

## 相關技能

- `php-development` — PHP 路由範例已更新為副檔名映射表
- `deployment-checklist` — 部署檢查清單

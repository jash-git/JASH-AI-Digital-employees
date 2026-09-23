---
name: site-link-audit
description: suanming 全站連結回歸偵測器——用瀏覽器 CDP 逐頁載入並點擊每個「相對路徑」連結，抓出 curl-only 巡檢會漏掉的子目錄頁面 404（T-37/T-38）
category: software-development
tags: [suanming, link-audit, cdp, qa, relative-path, regression]
---

# 全站連結回歸偵測器 (site-link-audit)

## 何時使用
任何新增或修改 `src/public/js/*.js`（尤其是**共用資料檔**如 articles.js、app.js，其內含文章卡片連結）之後，部署前跑一次。這是攔截「相對路徑連結在子目錄頁面點擊崩潰」歷史缺陷的自動化守門員。

## 背景（為什麼需要這個）
2026-09-19 全站連結巡檢發現：`js/cate/articles.js` 內所有文章連結用**相對路徑** `blog/detail.html?id=xxx`。瀏覽器會相對於「來源頁所在目錄」解析，所以：
- 從根目錄 `/blog/index.html` → 解析成 `/blog/blog/detail.html`…（實際在 /blog/ 下是 `detail.html` ✅）
- 從子目錄 `/cate/changshi.html` → 解析成 `/cate/blog/detail.html` ❌ **404**
- 從子目錄 `/type/dianji.html` → 解析成 `/type/blog/detail.html` ❌ **404**

**curl-only 巡檢完全沒抓到**：curl 把相對路徑解析到「網站根目錄」回 200，但瀏覽器實際從子目錄解析才崩潰。全站曾誤報「0 broken」卻無痕實測全 404（另有 .htaccess rewrite 的根因）。

受影響：**7 個頁面**（6 個 `/cate/*.html` + 1 個 `/type/dianji.html`），約 **31 張文章卡片全部點不通**。

## 工具位置與用法
```bash
# 預設掃描 /var/www/html（部署環境）
python3 scripts/site-link-audit.py

# 指定 docroot / base URL / CDP port
python3 scripts/site-link-audit.py --docroot /path/to/web --base http://host --port 9222

# FULL 模式：測試每個相對連結（非預設，較慢）
python3 scripts/site-link-audit.py --full
```
- exit code: `0` = 無崩潰連結、`1` = 發現 404、`2` = Chrome/CDP 無法連線。

## 正確寫法（子代理/開發者必須遵守）
共用資料檔內的文章連結，**一律用絕對路徑**（根相對 `/blog/detail.html`），不要用相對於來源頁的相對路徑：
```javascript
// ❌ 錯誤 — 從 /cate/、/type/ 子目錄點擊會崩潰
{ url:'blog/detail.html?id=1420', img:'blog/thumb_....webp' }

// ✅ 正確 — 無論來源頁在哪個目錄都解析到同一檔案
{ url:'/blog/detail.html?id=1420', img:'/blog/thumb_....webp' }
```
根因：相對路徑的解析基準是「點擊時所在的頁面」，跨目錄必崩。絕對路徑（`/` 開頭）的解析基準固定為網站根，全域一致。

## 驗證（建立後必做）
1. **正控測試**（修之前）：跑 `python3 scripts/site-link-audit.py --docroot /var/www/html` → 應列出 7 個崩潰頁面、exit=1。
2. **負控測試**（修之後）：把 articles.js/app.js 的相對路徑改成絕對路徑並部署 → 重跑 → 應回傳 `✅ No broken relative-path links found`、exit=0。

## 與既有技能的關係
- 此工具是 `jl-delegation-workflow`「陷阱3（curl HTTP 巡檢有盲區）」的**執行版**，專門補足 curl-only 偵測不到「相對路徑跨目錄崩潰」的缺口。
- 也補強 `cdp-web-test`：後者專注互動流程驗證（表單/下拉），本工具專注「跨頁面連結路徑回歸」。兩者互補。

## 維護
若發現其他類型連結崩潰模式（如 `.htaccess` catch-all rewrite、動態路由），在 `site-link-audit.py` 擴充對應偵測邏輯即可，不必另建新工具。
